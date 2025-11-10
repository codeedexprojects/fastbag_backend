from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)


def send_otp_2factor(mobile_number, otp):
    """
    Send your own custom OTP using 2Factor API
    This sends YOUR OTP, not 2Factor's auto-generated one
    """
    api_key = settings.TWO_FACTOR_API_KEY
    
    # Using the direct SMS endpoint with your OTP
    url = f"https://2factor.in/API/V1/{api_key}/SMS/{mobile_number}/{otp}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"2Factor Send Custom OTP Response: {data}")
        
        if data.get('Status') == 'Success':
            logger.info(f"Custom OTP {otp} sent successfully to {mobile_number}")
            return True
        else:
            error_msg = data.get('Details', 'Unknown error')
            logger.error(f"Failed to send custom OTP: {error_msg}")
            raise Exception(f"Failed to send OTP: {error_msg}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while sending OTP: {str(e)}")
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while sending OTP: {str(e)}")
        raise


from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth"""
    R = 6371  # Earth radius in KM
    dlat = radians(float(lat2) - float(lat1))
    dlon = radians(float(lon2) - float(lon1))
    a = sin(dlat / 2) ** 2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c