#!/usr/bin/env python3
"""
Deploy functions to OpenWebUI.
Usage: python scripts/deploy.py
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()


class Deployer:
    def __init__(self):
        self.base_url = os.getenv('OPENWEBUI_URL', 'http://localhost:3000')
        self.api_key = os.getenv('OPENWEBUI_API_KEY')

        if not self.api_key:
            print("❌ OPENWEBUI_API_KEY not set in .env")
            sys.exit(1)

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def deploy_function(self, function_file: Path) -> bool:
        """Deploy a single function file"""

        print(f"\n📤 Deploying: {function_file.name}")

        with open(function_file, 'r') as f:
            content = f.read()

        # Extract metadata from docstring
        metadata = self._extract_metadata(content)

        payload = {
            "id": metadata['id'],
            "name": metadata['title'],
            "content": content,
            "version": metadata['version'],
            "enabled": True
        }

        try:
            # Try to create new function
            response = requests.post(
                f"{self.base_url}/api/v1/functions",
                headers=self.headers,
                json=payload
            )

            if response.status_code == 409:
                # Function exists, update it
                print(f"   Function exists, updating...")
                response = requests.put(
                    f"{self.base_url}/api/v1/functions/{metadata['id']}",
                    headers=self.headers,
                    json=payload
                )

            response.raise_for_status()
            print(f"   ✅ Deployed: {metadata['title']} v{metadata['version']}")
            return True

        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            return False

    def _extract_metadata(self, code: str) -> dict:
        """Extract metadata from function docstring"""
        lines = code.split('\n')
        metadata = {
            'title': 'Unknown',
            'version': '0.0.0',
            'id': 'unknown'
        }

        for line in lines:
            if 'title:' in line:
                metadata['title'] = line.split('title:')[1].strip()
            elif 'version:' in line:
                metadata['version'] = line.split('version:')[1].strip()
            elif 'FUNCTION_NAME' in line and '=' in line:
                function_name = line.split('=')[1].strip().strip('"\'')
                metadata['id'] = function_name

        return metadata

    def deploy_all(self):
        """Deploy all functions in functions/ directory"""

        functions_dir = Path(__file__).parent.parent / 'functions'
        function_files = list(functions_dir.glob('client_*.py'))

        if not function_files:
            print("❌ No function files found (client_*.py)")
            return False

        print(f"\n🚀 Deploying {len(function_files)} functions to {self.base_url}")

        results = []
        for func_file in function_files:
            success = self.deploy_function(func_file)
            results.append(success)

        # Summary
        total = len(results)
        successful = sum(results)

        print(f"\n{'='*50}")
        print(f"📊 Deployment Summary: {successful}/{total} functions deployed")
        print(f"{'='*50}\n")

        return all(results)


def main():
    deployer = Deployer()
    success = deployer.deploy_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
