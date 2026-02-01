#!/usr/bin/env python3
"""
Backup OpenWebUI settings before deployment.
"""

import os
import requests
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def backup_settings():
    """Backup OpenWebUI configurations"""

    base_url = os.getenv('OPENWEBUI_URL', 'http://localhost:3000')
    api_key = os.getenv('OPENWEBUI_API_KEY')

    if not api_key:
        print("❌ OPENWEBUI_API_KEY not set")
        return False

    headers = {"Authorization": f"Bearer {api_key}"}

    # Create backup directory
    backup_dir = Path(__file__).parent.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print(f"\n💾 Creating backup: {timestamp}")

    try:
        # Backup functions
        print("   Backing up functions...")
        response = requests.get(f"{base_url}/api/v1/functions", headers=headers)
        response.raise_for_status()

        with open(backup_dir / f'functions_{timestamp}.json', 'w') as f:
            json.dump(response.json(), f, indent=2)

        print("   ✅ Functions backed up")

        # Backup models (if endpoint exists)
        try:
            print("   Backing up models...")
            response = requests.get(f"{base_url}/api/v1/models", headers=headers)
            if response.status_code == 200:
                with open(backup_dir / f'models_{timestamp}.json', 'w') as f:
                    json.dump(response.json(), f, indent=2)
                print("   ✅ Models backed up")
        except:
            print("   ⚠️  Models endpoint not available")

        print(f"\n✅ Backup completed: {timestamp}\n")
        return True

    except Exception as e:
        print(f"\n❌ Backup failed: {str(e)}\n")
        return False


if __name__ == "__main__":
    import sys
    success = backup_settings()
    sys.exit(0 if success else 1)
