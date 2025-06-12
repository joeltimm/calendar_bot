# ~/calendar_bot/utils/tenacity_utils.py
#This is to make sure the bot only sends emails if retry errors fail
from utils.logger import logger
from utils.email_utils import send_error_email

def log_and_email_on_final_failure(retry_state):


#    Callback for tenacity to log and email AFTER all retries have failed.
#    This function is executed only when the retried operation has permanently failed.
    exception = retry_state.outcome.exception()
    # Get the name of the function that failed for the email subject
    failed_function_name = retry_state.fn.__name__

    logger.error(
        f"❌ FINAL ATTEMPT FAILED for '{failed_function_name}'.",
        exc_info=exception
    )
    send_error_email(
        f"Calendar Bot - Permanent Error in {failed_function_name}",
        f"The bot encountered a permanent error that could not be resolved after multiple retries.\n\n"
        f"Function: {failed_function_name}\n"
        f"Arguments: {retry_state.args}\n"
        f"Final error:\n{exception}"
    )

def log_before_retry(retry_state):

#    Callback to log that a retry is about to happen. This gives visibility
#    into transient errors without sending an email.
    logger.warning(
        f"⚠️ Transient API error in '{retry_state.fn.__name__}'. "
        f"Retrying in {retry_state.next_action.sleep:.2f} seconds... "
        f"(Attempt #{retry_state.attempt_number})"
    )
