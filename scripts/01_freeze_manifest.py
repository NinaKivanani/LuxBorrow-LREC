#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, json, hashlib, platform
from pathlib import Path
import yaml
from datetime import datetime, timezone


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_dir(d: Path) -> dict:
    out = {}
    for p in sorted(d.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(d))] = sha256_file(p)
    return out


def main():
    cfg_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]

    manifests = Path(paths["manifests"])
    manifests.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "python": sys.version,
        "platform": platform.platform(),
        "config": cfg_path,
        "hashes": {},
    }

    # Hash RTL inputs
    raw_dir = Path(paths["raw_dir"])
    if not raw_dir.exists():
        raise SystemExit(f"Missing input directory {raw_dir}")
    manifest["hashes"]["rtl_raw"] = sha256_dir(raw_dir)

    # Resources
    patt = Path(paths["pattern_file"])
    if not patt.exists():
        raise SystemExit(f"Missing resource at {patt}")
    manifest["hashes"]["patterns_with_examples.json"] = sha256_file(patt)

    loan = Path(paths.get("loanwords_json", ""))
    if loan and loan.exists():
        manifest["hashes"]["lux_loanwords.ud.json"] = sha256_file(loan)
    else:
        manifest["hashes"]["lux_loanwords.ud.json"] = "SKIPPED"

    # Optional UD model (check both paths and plots sections)
    udm_path = paths.get("udpipe_model") or cfg.get("plots", {}).get("udpipe_model", "")
    udm = Path(udm_path) if udm_path else None
    if udm and udm.exists() and udm.is_file():
        manifest["hashes"]["udpipe_model"] = sha256_file(udm)
    else:
        manifest["hashes"]["udpipe_model"] = "SKIPPED (tokenizer-only pipeline)"

    outp = manifests / "freeze_manifest.json"
    outp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", outp)


if __name__ == "__main__":
    main()


