#!/usr/bin/env python3
"""Vérifie le catalogue de ressources du CyberDev Dojo avec de vraies données.

Deux niveaux de contrôle, honnêtement distingués :

1. **GitHub** — quand une ressource déclare ``repo: owner/nom``, on interroge
   ``api.github.com`` : étoiles, licence, dernière mise à jour, archivage. Ce sont des
   données réelles, rafraîchies à chaque exécution.
2. **Joignabilité HTTP** — on tente un HEAD/GET sur chaque URL. Si le réseau de
   l'environnement est restreint (bac à sable, CI sans sortie), le résultat est
   ``reseau_indisponible`` : la ressource reste marquée « non vérifiée », jamais
   « valide » par défaut.

Le résultat est écrit dans ``backend/curriculum/resources-verified.json`` et exposé par
l'API (``GET /api/resources``).

Usage::

    python3 scripts/check_resources.py              # vérifie et écrit l'overlay
    python3 scripts/check_resources.py --dry-run    # affiche sans écrire
    python3 scripts/check_resources.py --only-github # saute les tests HTTP
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "backend" / "curriculum" / "roadmap-12-semaines.json"
OUTPUT_PATH = ROOT / "backend" / "curriculum" / "resources-verified.json"

USER_AGENT = "shellforge-resource-check/1.0"


def _request(url: str, timeout: int = 15, method: str = "GET") -> tuple[int | None, str]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    if "api.github.com" in url:
        request.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, ""
    except urllib.error.HTTPError as exc:
        return exc.code, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return None, str(getattr(exc, "reason", exc))[:120]


def github_metadata(repo: str) -> dict:
    """Métadonnées réelles d'un dépôt GitHub, ou erreur explicite."""
    url = f"https://api.github.com/repos/{repo}"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        return {"repo": repo, "error": f"HTTP {exc.code}"}
    except (urllib.error.URLError, OSError) as exc:
        return {"repo": repo, "error": str(getattr(exc, "reason", exc))[:120]}
    return {
        "repo": repo,
        "full_name": data["full_name"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "license": (data.get("license") or {}).get("spdx_id"),
        "language": data.get("language"),
        "archived": data["archived"],
        "pushed_at": data["pushed_at"][:10],
        "created_at": data["created_at"][:10],
        "description": (data.get("description") or "")[:200],
        "html_url": data["html_url"],
    }


def collect_items(resources: dict) -> list[dict]:
    items = list(resources.get("recommended", []))
    for category in resources.get("categories", []):
        items.extend(category.get("items", []))
    return items


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Vérifie les ressources du dojo")
    parser.add_argument("--dry-run", action="store_true", help="affiche sans écrire le fichier")
    parser.add_argument("--only-github", action="store_true", help="ne teste pas les URL hors GitHub")
    parser.add_argument("--timeout", type=int, default=15, help="délai HTTP par URL (s)")
    args = parser.parse_args(argv)

    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    items = collect_items(roadmap["resources"])

    results: dict[str, dict] = {}
    reachable = unreachable = 0

    for entry in items:
        url = entry["url"]
        record: dict = {"url": url, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

        repo = entry.get("repo")
        if repo:
            meta = github_metadata(repo)
            record["github"] = meta
            if meta.get("error"):
                print(f"  ! {entry['name']:38} GitHub KO ({meta['error']})")
            else:
                print(
                    f"  ✓ {entry['name']:38} ★{meta['stars']:>7}  {meta['license'] or 'n/a':<12} "
                    f"maj {meta['pushed_at']}  {'ARCHIVÉ' if meta['archived'] else ''}"
                )

        if not args.only_github:
            status, error = _request(url, timeout=args.timeout)
            if status:
                record["http_status"] = status
                reachable += 1
            else:
                record["http_status"] = None
                record["network_error"] = error or "injoignable"
                unreachable += 1

        results[url] = record

    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": {
            "github": "api.github.com/repos/{owner}/{repo} (étoiles, licence, archivage, dernière poussée)",
            "http": "requête HTTP directe sur chaque URL depuis l'environnement d'exécution",
        },
        "counts": {
            "resources": len(items),
            "http_checked": not args.only_github,
            "http_reachable": reachable,
            "http_unreachable": unreachable,
            "github_checked": sum(1 for r in results.values() if "github" in r),
        },
        "resources": results,
    }

    print(
        f"\n{len(items)} ressources · GitHub vérifié : {payload['counts']['github_checked']} · "
        f"HTTP joignables : {reachable} · injoignables depuis cet environnement : {unreachable}"
    )
    if unreachable and not args.only_github:
        print(
            "Note : les URL injoignables ne sont pas déclarées invalides — l'environnement "
            "n'a peut-être pas de sortie réseau vers ces hôtes."
        )

    if args.dry_run:
        print("(dry-run : fichiers inchangés)")
        return 0

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"écrit : {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
