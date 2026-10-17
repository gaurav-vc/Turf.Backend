"""
Player Intake & Roster Service
Ported from Cricket Auction Phase 2 V24 authoritative logic.
Handles Excel (.xlsx), CSV, dynamic custom fields discovery, and registration tokens.
"""
import io
import csv
import json
import uuid
import secrets
from decimal import Decimal
from django.db import transaction
from accounts.models import User, PlayerProfile
from ..models import Auction, AuctionPlayer
from ..models_v24 import CustomFieldDefinition, CustomFieldOption, CustomFieldValue, AuctionCategory

class PlayerIntakeService:
    @staticmethod
    def parse_file(uploaded_file):
        """
        Parses an uploaded CSV or XLSX file and returns list of dictionaries and headers.
        """
        filename = (uploaded_file.name or '').lower()
        raw_bytes = uploaded_file.read()

        if not raw_bytes:
            raise ValueError("Uploaded file is empty.")

        if filename.endswith('.xlsx'):
            from openpyxl import load_workbook
            wb = load_workbook(filename=io.BytesIO(raw_bytes), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()

            if not rows:
                raise ValueError("Excel file contains no data.")

            headers = [str(cell).strip() if cell is not None else '' for cell in rows[0]]
            data = []
            for r in rows[1:]:
                if any(v is not None and str(v).strip() != '' for v in r):
                    row_dict = {headers[i]: r[i] for i in range(len(headers)) if i < len(r)}
                    data.append(row_dict)
            return data, headers

        elif filename.endswith('.csv'):
            try:
                text = raw_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw_bytes.decode('cp1252')

            reader = csv.DictReader(io.StringIO(text))
            data = list(reader)
            headers = reader.fieldnames or []
            return data, headers

        else:
            raise ValueError("Please upload an Excel (.xlsx) or CSV file.")

    @staticmethod
    def auto_learn_option(field_def, value):
        """
        Learns and persists distinct options for select/multiselect fields dynamically.
        """
        val_str = str(value or '').strip()
        if not val_str:
            return

        exists = field_def.options.filter(option_value__iexact=val_str).exists()
        if not exists:
            order = field_def.options.count() + 1
            CustomFieldOption.objects.create(
                field_definition=field_def,
                option_value=val_str,
                display_order=order
            )

    @staticmethod
    def import_players(auction, rows, headers, user_creator=None):
        """
        Imports players into the auction, discovers categories, and learns custom field options.
        """
        # Normalise header lookup
        header_map = {str(h).strip().lower(): h for h in headers if h}

        imported_count = 0
        errors = []

        # Find next serial_no
        last_serial = auction.players.order_by('-serial_no').first()
        next_serial = (last_serial.serial_no or 0) + 1 if last_serial else 1

        for idx, row in enumerate(rows):
            try:
                def get_val(*aliases):
                    for a in aliases:
                        if a.lower() in header_map:
                            val = row.get(header_map[a.lower()])
                            if val is not None and str(val).strip():
                                return str(val).strip()
                    return ""

                name = get_val('name', 'player name', 'player_name', 'fullname')
                if not name:
                    continue # Skip empty name rows

                mobile = get_val('mobile', 'phone', 'contact', 'mobile number')
                cat_name = get_val('category', 'player category', 'cat') or "General"
                role_name = get_val('role', 'player role', 'skill', 'skills') or "All-Rounder"
                batting = get_val('batting style', 'batting', 'batting_style')
                bowling = get_val('bowling style', 'bowling', 'bowling_style')
                location = get_val('location', 'city', 'area')
                photo_url = get_val('photo url', 'photo', 'image', 'photo_url')
                base_raw = get_val('base price', 'base_price', 'price')
                
                try:
                    base_price = Decimal(str(base_raw).replace(',', '')) if base_raw else Decimal('1000.00')
                except Exception:
                    base_price = Decimal('1000.00')

                age_raw = get_val('age')
                age = int(age_raw) if age_raw.isdigit() else None

                serial_raw = get_val('player no.', 'player no', 'serial no', 'serial_no', 'no')
                if serial_raw and serial_raw.isdigit():
                    serial_no = int(serial_raw)
                else:
                    serial_no = next_serial
                    next_serial += 1

                with transaction.atomic():
                    # Ensure Category exists
                    cat_obj = auction.categories.filter(name__iexact=cat_name).first()
                    if not cat_obj:
                        cat_obj = AuctionCategory.objects.create(
                            auction=auction,
                            name=cat_name,
                            base_price=base_price,
                            target_count=0
                        )

                    # Create or find User
                    uname = f"auc_{uuid.uuid4().hex[:8]}"
                    p_email = f"{uname}@turfarena.local"
                    player_user = User.objects.create(
                        username=uname,
                        email=p_email,
                        full_name=name,
                        first_name=name,
                        user_type='PLAYER'
                    )

                    # Create AuctionPlayer
                    auc_player = AuctionPlayer.objects.create(
                        auction=auction,
                        player=player_user,
                        serial_no=serial_no,
                        category=cat_obj.name,
                        role=role_name,
                        batting_style=batting,
                        bowling_style=bowling,
                        location=location,
                        mobile=mobile,
                        age=age,
                        base_price=base_price,
                        photo_url=photo_url,
                        registration_source='Excel/CSV',
                        status='AVAILABLE'
                    )

                    # Collect custom fields
                    custom_data = {}
                    for field_def in auction.custom_fields.all():
                        f_val = get_val(field_def.field_key, field_def.label)
                        if f_val:
                            custom_data[field_def.field_key] = f_val
                            if field_def.data_type in ['select', 'multiselect']:
                                PlayerIntakeService.auto_learn_option(field_def, f_val)

                            CustomFieldValue.objects.update_or_create(
                                field_definition=field_def,
                                entity_id=auc_player.id,
                                defaults={'value_text': f_val}
                            )

                    auc_player.custom_data = custom_data
                    auc_player.save()
                    imported_count += 1

            except Exception as e:
                errors.append(f"Row {idx+2}: {str(e)}")

        return imported_count, errors

    @staticmethod
    def ensure_registration_token(auction):
        """
        Creates or returns public tokenized registration link for the tournament auction.
        """
        reg_link = getattr(auction, 'registration_link', None)
        if not reg_link:
            token = secrets.token_urlsafe(20)
            from ..models_v24 import PlayerRegistrationLink
            reg_link = PlayerRegistrationLink.objects.create(
                auction=auction,
                registration_token=token,
                enabled=True,
                title=f"{auction.name} - Player Registration"
            )
        return reg_link
