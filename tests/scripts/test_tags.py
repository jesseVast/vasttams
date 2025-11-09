#!/usr/bin/env python3
"""
Simple script to test tag operations including list values.

Usage:
    python test_tags.py [--server-url URL] [--username USER] [--password PASS]
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add src/client to path for imports
client_path = Path(__file__).parent.parent.parent / "src" / "client"
if str(client_path) not in sys.path:
    sys.path.insert(0, str(client_path))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSClientError


async def main():
    parser = argparse.ArgumentParser(description="Simple TAMS tag test")
    parser.add_argument("--server-url", default="http://localhost:8000", help="TAMS server URL")
    parser.add_argument("--username", default="admin", help="Username")
    parser.add_argument("--password", default="vastdata", help="Password")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Simple TAMS Tag Test")
    print("=" * 80)
    
    try:
        # Create client
        print(f"\n[1] Connecting to TAMS server: {args.server_url}")
        client = TAMSClient(
            server_url=args.server_url,
            username=args.username,
            password=args.password,
            timeout=60
        )
        
        async with client:
            # Create source
            print("\n[2] Creating source...")
            source = client.TAMSSource(
                format="urn:x-nmos:format:video",
                label="Tag Test Source"
            )
            await source._ensure_created()
            print(f"✅ Created source: {source.id} - {source.label}")
            
            # Create flow
            print("\n[3] Creating flow...")
            flow = source.TAMSFlow(
                format="urn:x-nmos:format:video",
                codec="video/h264",
                label="Tag Test Flow",
                frame_width=1920,
                frame_height=1080,
                frame_rate={"numerator": 25, "denominator": 1}
            )
            await flow._ensure_created()
            print(f"✅ Created flow: {flow.id} - {flow.label}")
            
            # Test string tag
            print("\n[4] Setting string tag on source...")
            await source.set_tag("environment", "test")
            tags = await source.get_tags()
            print(f"✅ Source tags: {tags}")
            assert "environment" in tags
            assert tags["environment"] == "test"
            
            # Test string tag on flow
            print("\n[5] Setting string tag on flow...")
            await flow.set_tag("quality", "hd")
            tags = await flow.get_tags()
            print(f"✅ Flow tags: {tags}")
            assert "quality" in tags
            assert tags["quality"] == "hd"
            
            # Test list tag on flow
            print("\n[6] Setting list tag on flow...")
            await flow.set_tag("formats", ["hd", "4k", "uhd"])
            tags = await flow.get_tags()
            print(f"✅ Flow tags after list: {tags}")
            assert "formats" in tags
            assert isinstance(tags["formats"], list)
            assert tags["formats"] == ["hd", "4k", "uhd"]
            
            # Test updating list tag
            print("\n[7] Updating list tag...")
            await flow.set_tag("formats", ["hd", "4k"])
            tags = await flow.get_tags()
            print(f"✅ Flow tags after update: {tags}")
            assert "formats" in tags
            assert isinstance(tags["formats"], list)
            assert tags["formats"] == ["hd", "4k"]
            
            # Test getting specific tag
            print("\n[8] Getting specific tag...")
            quality = await flow.get_tag("quality")
            formats = await flow.get_tag("formats")
            print(f"✅ quality tag: {quality}")
            print(f"✅ formats tag: {formats}")
            assert quality == "hd"
            assert isinstance(formats, list)
            assert formats == ["hd", "4k"]
            
            # Test deleting tag
            print("\n[9] Deleting tag...")
            await flow.delete_tag("quality")
            tags = await flow.get_tags()
            print(f"✅ Flow tags after delete: {tags}")
            assert "quality" not in tags
            assert "formats" in tags  # Should still be there
            
            # Cleanup
            print("\n[10] Cleaning up...")
            try:
                await flow.delete()
                print("✅ Deleted flow")
                await source.delete()
                print("✅ Deleted source")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
            
            print("\n" + "=" * 80)
            print("✅ Tag test completed successfully!")
            print("=" * 80)
            return 0
            
    except TAMSClientError as e:
        print(f"\n❌ TAMS Client Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

