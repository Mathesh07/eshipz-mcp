import json
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os 

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("eshipz_tracking")

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "https://app.eshipz.com")
ESHIPZ_API_TRACKING_URL = f"{API_BASE_URL}/api/v2/trackings"
ESHIPZ_TOKEN = os.getenv("ESHIPZ_TOKEN", "")

async def make_nws_request(tracking_number: str) -> dict[str, Any] | None:
    headers = {
        "Content-Type": "application/json",
        "X-API-TOKEN": ESHIPZ_TOKEN
    }
    payload = json.dumps({"track_id": tracking_number})
    async with httpx.AsyncClient() as client:
        try:
            # Note: Verify if your API expects data=payload or json=payload
            # Standard libraries often prefer json=... to handle serialization automatically
            response = await client.post(ESHIPZ_API_TRACKING_URL, headers=headers, timeout=30.0, data=payload)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def _format_carrier(slug: str) -> str:
    """Format carrier name for display"""
    return slug.upper() if slug else "Unknown Carrier"


def _create_summary(shipment: dict) -> str:
    """Create human-readable summary based on shipment status"""
    
    tracking_num = shipment.get("tracking_number", "Unknown")
    carrier = _format_carrier(shipment.get("slug"))
    status = shipment.get("tag")
    checkpoints = shipment.get("checkpoints", [])
    latest = checkpoints[0] if checkpoints else {}
    
    location = latest.get("city", "")
    remark = latest.get("remark", "")
    delivery_date = shipment.get("delivery_date")
    eta = shipment.get("expected_delivery_date")
    
    # Status-specific formatting
    if status == "Delivered":
        summary = f" Delivered via {carrier}"
        if delivery_date:
            summary += f" on {delivery_date}"
        if location:
            summary += f" at {location}"
        return summary
    
    elif status == "OutForDelivery":
        summary = f" Out for delivery via {carrier}"
        if location:
            summary += f" from {location}"
        return summary
    
    elif status == "InTransit":
        summary = f"In transit via {carrier}"
        if location:
            summary += f", currently in {location}"
        if remark:
            summary += f" - {remark}"
        if eta:
            summary += f"\n   Expected delivery: {eta}"
        return summary
    
    elif status == "Exception":
        summary = f"Exception via {carrier}"
        if location:
            summary += f" at {location}"
        if remark:
            summary += f" - {remark}"
        return summary
    
    elif status == "PickedUp":
        summary = f"Picked up via {carrier}"
        if location:
            summary += f" from {location}"
        return summary
    
    elif status == "InfoReceived":
        return f"Shipment information received by {carrier}"
    
    else:
        summary = f"{status} via {carrier}" if status else f"Tracking {tracking_num} via {carrier}"
        if location and remark:
            summary += f" - {remark} ({location})"
        elif remark:
            summary += f" - {remark}"
        return summary


@mcp.tool()
async def get_tracking(tracking_number: str) -> str:
    """Get tracking information for a shipment"""
    data = await make_nws_request(tracking_number)
    
    if not data:
        return " Tracking information could not be retrieved. Please verify the tracking number."

    try:
        if isinstance(data, list) and len(data) > 0:
            shipment = data[0]
        else:
            return "No shipment data found in the response."

        # Get summary
        summary = _create_summary(shipment)
        
        # Add latest update timestamp if available
        checkpoints = shipment.get("checkpoints", [])
        if checkpoints:
            latest_time = checkpoints[0].get("date", "")
            if latest_time:
                summary += f"\n   Last updated: {latest_time}"
        
        # Add event count
        event_count = len(checkpoints)
        if event_count > 0:
            summary += f"\n   Total events: {event_count}"
        
        return summary

    except Exception as e:
        return f"Error processing tracking data: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')