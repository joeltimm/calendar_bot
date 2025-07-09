import logging
import sys
import os 
from pathlib import Path

# --- Add project root to sys.path ---
# This assumes this test script is in 'calendar_bot/tests/'
# and the 'common' module is in 'calendar_bot/common/'
try:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    print(f"--- test_credentials.py: Added project root to sys.path: {project_root} ---")
except IndexError:
    print("--- test_credentials.py: Could not determine project root. Make sure the script is in a subdirectory (e.g., 'tests'). ---")
    sys.exit(1)


# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

logger.info("--- Logging configured, attempting imports for test_credentials.py ---")

try:
    from common.credentials import load_credentials, load_gmail_credentials, BASE
    from googleapiclient.discovery import build # Keep if you use service building in tests
    logger.info("Successfully imported 'common.credentials' and 'googleapiclient.discovery.build'.")
except ModuleNotFoundError as e_module:
    error_msg = f"CRITICAL ERROR: ModuleNotFoundError during import: {e_module}. Ensure 'common' directory is in project root."
    print(error_msg) # Print as logger might not be fully working if basicConfig had issues
    logger.error(error_msg)
    sys.exit(1)
except Exception as e_import:
    error_msg = f"CRITICAL ERROR: An unexpected error occurred during import: {e_import}"
    print(error_msg)
    logger.error(error_msg, exc_info=True)
    sys.exit(1)


def test_specific_credential(load_function, user_identifier, service_name, expected_scopes):
    logger.info(f"--- Testing {service_name} credentials for '{user_identifier if user_identifier else 'default (joeltimm_gmail)'}' ---")
    try:
        if user_identifier:
            creds = load_function(user_identifier)
        else: # For load_gmail_credentials() which is hardcoded for joeltimm
            creds = load_function()

        if creds:
            logger.info(f"✅ Successfully loaded {service_name} credentials.")
            
            # Construct the expected token path for logging based on how functions in credentials.py work
            if load_function.__name__ == 'load_gmail_credentials':
                token_file_name = "token_joeltimm.json"
            elif user_identifier:
                token_file_name = f"token_{user_identifier}.json"
            else: # Should not happen with current functions
                token_file_name = "unknown_token.json"
            logger.info(f"   Expected token file being used (by credentials.py logic): {BASE / token_file_name}")
            
            if creds.expired:
                logger.warning("   ⚠️ Token was expired and should have been refreshed.")
            else:
                logger.info("   Token is currently valid (not expired).")

            # Check if the loaded creds object has the scopes requested by the load function
            # Note: creds.scopes reflects scopes with which this specific Credentials object was initialized,
            # not necessarily ALL scopes present in the underlying token file.
            missing_scopes_in_creds_obj = [scope for scope in expected_scopes if scope not in creds.scopes]
            if missing_scopes_in_creds_obj:
                logger.error(f"   ❌ ERROR: Loaded 'Credentials' object is missing expected scopes: {missing_scopes_in_creds_obj}. 'Credentials' object scopes: {creds.scopes}")
            else:
                logger.info(f"   ✅ Loaded 'Credentials' object has all expected scopes for this load: {expected_scopes}. 'Credentials' object scopes: {creds.scopes}")

            # Optional: Try to build the service (basic test)
            try:
                service_to_build = None
                if "calendar" in service_name.lower():
                    service_to_build = 'calendar'
                    version = 'v3'
                elif "gmail" in service_name.lower():
                    service_to_build = 'gmail'
                    version = 'v1'
                
                if service_to_build:
                    service_obj = build(service_to_build, version, credentials=creds)
                    logger.info(f"   Successfully built Google {service_to_build.capitalize()} service object.")
                    # Example API calls (read-only, safe to run):
                    # if service_to_build == 'calendar':
                    #     service_obj.calendarList().list(maxResults=1).execute()
                    #     logger.info("      Successfully made a basic API call: calendarList().list()")
                    # elif service_to_build == 'gmail':
                    #     service_obj.users().getProfile(userId='me').execute()
                    #     logger.info("      Successfully made a basic API call: users().getProfile()")
            except Exception as e_service:
                logger.error(f"   ❌ ERROR building service or making API call for {service_name}: {e_service}", exc_info=False)


        else:
            logger.error(f"❌ Failed to load {service_name} credentials. 'creds' object is None.")

    except FileNotFoundError as e_fnf:
        logger.error(f"❌ FileNotFoundError for {service_name}: {e_fnf}")
    except Exception as e_test:
        logger.error(f"❌ An unexpected error occurred testing {service_name}: {e_test}", exc_info=True)
    logger.info(f"--- Test Complete for {service_name} ---\n")


if __name__ == "__main__":
    logger.info("--- test_credentials.py: Main test execution started ---")

    # Test Joeltimm's combined token for Calendar access
    test_specific_credential(
        load_function=load_credentials,
        user_identifier="joeltimm",
        service_name="Joeltimm Calendar",
        expected_scopes=['https://www.googleapis.com/auth/calendar']
    )

    # Test Joeltimm's combined token for Gmail access
    test_specific_credential(
        load_function=load_gmail_credentials,
        user_identifier=None, # load_gmail_credentials is specific to joeltimm
        service_name="Joeltimm Gmail",
        expected_scopes=['https://www.googleapis.com/auth/gmail.send']
    )

    # Test Tsouthworth's token for Calendar access
    test_specific_credential(
        load_function=load_credentials,
        user_identifier="tsouthworth",
        service_name="Tsouthworth Calendar",
        expected_scopes=['https://www.googleapis.com/auth/calendar']
    )

    logger.info("--- All credential loading tests finished ---")