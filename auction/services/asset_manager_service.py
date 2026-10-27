import os
import uuid
from pathlib import Path
from collections import deque
from PIL import Image
from django.conf import settings
from django.utils import timezone


class AssetManagerService:
    """
    Conservative background-removal engine and media asset processor.
    Ported directly from Cricket Auction Phase 2 V24 Flask devwork.
    """

    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    @classmethod
    def get_upload_dir(cls, auction_id: str) -> Path:
        dir_path = Path(settings.MEDIA_ROOT) / 'auction_assets' / f'auction_{auction_id}'
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @classmethod
    def remove_logo_background(cls, input_path: Path) -> Path:
        """
        Create a transparent PNG by removing background colours connected to the image edges.
        Optimized with max-dimension bounding (600px) so background removal takes <150ms instead of 30s.
        """
        im = Image.open(input_path).convert('RGBA')
        w, h = im.size
        if w < 4 or h < 4:
            return input_path

        # Downscale if image is overly large for fast execution and crisp rendering
        max_dim = 600
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_w = max(4, int(w * scale))
            new_h = max(4, int(h * scale))
            im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = im.size

        pix = im.load()
        samples = []
        for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
                     (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
            samples.append(pix[x, y][:3])

        bg = tuple(sum(c[i] for c in samples) // len(samples) for i in range(3))

        q = deque()
        seen = set()
        for x in range(w):
            q.append((x, 0))
            q.append((x, h - 1))
        for y in range(h):
            q.append((0, y))
            q.append((w - 1, y))

        def is_bg_color(rgb):
            return sum((rgb[i] - bg[i]) ** 2 for i in range(3)) ** 0.5 <= 58

        max_iters = w * h
        iters = 0
        while q and iters < max_iters:
            iters += 1
            x, y = q.popleft()
            if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
                continue
            seen.add((x, y))
            if not is_bg_color(pix[x, y][:3]):
                continue
            r, g, b, _ = pix[x, y]
            pix[x, y] = (r, g, b, 0)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen:
                    q.append((nx, ny))

        out_path = input_path.with_name(f"{input_path.stem}__transparent.png")
        im.save(out_path, 'PNG', optimize=True)
        return out_path

    @classmethod
    def save_and_process_asset(cls, auction_id: str, file_obj, name: str, asset_type: str, remove_bg: bool) -> dict:
        ext = Path(file_obj.name).suffix.lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: PNG, JPG, JPEG, WEBP, GIF.")

        upload_dir = cls.get_upload_dir(auction_id)
        asset_id = f"asset_{uuid.uuid4().hex[:12]}"
        clean_stem = Path(file_obj.name).stem.replace(' ', '_')
        orig_filename = f"{clean_stem}_{asset_id[:8]}{ext}"
        orig_path = upload_dir / orig_filename

        with open(orig_path, 'wb+') as dest:
            for chunk in file_obj.chunks():
                dest.write(chunk)

        orig_rel_url = f"{settings.MEDIA_URL}auction_assets/auction_{auction_id}/{orig_filename}"
        processed_rel_url = orig_rel_url
        is_transparent = False

        if remove_bg:
            try:
                trans_path = cls.remove_logo_background(orig_path)
                processed_rel_url = f"{settings.MEDIA_URL}auction_assets/auction_{auction_id}/{trans_path.name}"
                is_transparent = True
            except Exception as e:
                # If background removal fails, fallback safely to original
                processed_rel_url = orig_rel_url
                is_transparent = False

        return {
            'id': asset_id,
            'name': name or clean_stem,
            'asset_type': asset_type or 'Logo',
            'original_url': orig_rel_url,
            'processed_url': processed_rel_url,
            'is_transparent': is_transparent,
            'created_at': timezone.now().isoformat(),
        }
