# import logging
# import threading
# import time
# from django.contrib.auth import get_user_model
# from django.test import TransactionTestCase
# from django.db import transaction, connection
# from django.core.exceptions import ObjectDoesNotExist
# # from users.models.employee import User

# logger = logging.getLogger('users')

# User = get_user_model()

# class UserConcurrencyTestCase(TransactionTestCase):
#     """Test case for handling concurrent updates to User model."""
#     def setUp(self):
#         """Set up test data."""
#         logger.info("Setting up UserConcurrencyTestCase")
#         try:
#             # Set transaction isolation level to SERIALIZABLE
#             with connection.cursor() as cursor:
#                 cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
#             # Create user within a transaction to ensure it's committed
#             with transaction.atomic():
#                 self.user = User.objects.create_user(
#                     username='testuser',
#                     email='test@example.com',
#                     password='Test@1234',
#                     first_name='Test',
#                     last_name='User',
#                     role='FIN_MANAGER'
#                 )
#             # Verify user exists
#             self.user = User.objects.get(id=self.user.id)
#             logger.info(f"Test user created: {self.user.username} (id={self.user.id})")
#         except Exception as e:
#             logger.error(f"Error setting up test user: {e}", exc_info=True)
#             raise

#     def tearDown(self):
#         """Clean up test data."""
#         logger.debug("Tearing down UserConcurrencyTestCase")
#         super().tearDown()  # Let Django handle connection cleanup

#     def test_concurrent_user_update(self):
#         """Test concurrent updates to the same user record."""
#         logger.info(f"Starting concurrent update test for user: {self.user.username}")

#         def update_user_first_name(user_id, first_name, delay=0.2, retries=3, retry_delay=0.5):
#             logger.debug(f"Thread updating user id={user_id} with first_name={first_name}")
#             for attempt in range(retries):
#                 try:
#                     with transaction.atomic():
#                         user = User.objects.select_for_update().get(id=user_id)
#                         time.sleep(delay)
#                         user.first_name = first_name
#                         user.save(user=user)
#                         logger.info(f"User id={user_id} updated with first_name={first_name}")
#                         break
#                 except ObjectDoesNotExist:
#                     logger.warning(f"User id={user_id} not found on attempt {attempt + 1}, retrying...")
#                     time.sleep(retry_delay)
#                     if attempt == retries - 1:
#                         logger.error(f"Failed to update user id={user_id} after {retries} attempts")
#                         raise
#                 except Exception as e:
#                     logger.error(f"Error in update_user_first_name: {e}", exc_info=True)
#                     raise

#         original_first_name = self.user.first_name
#         thread1 = threading.Thread(
#             target=update_user_first_name,
#             args=(self.user.id, 'Alice', 0.2)
#         )
#         thread2 = threading.Thread(
#             target=update_user_first_name,
#             args=(self.user.id, 'Bob', 0)
#         )

#         logger.debug("Starting concurrent update threads")
#         thread1.start()
#         thread2.start()
#         thread1.join()
#         thread2.join()

#         try:
#             self.user.refresh_from_db()
#             logger.info(f"User after concurrent update: first_name={self.user.first_name}")
#             self.assertTrue(
#                 self.user.first_name in ('Alice', 'Bob'),
#                 f"Expected first_name to be 'Alice' or 'Bob', got '{self.user.first_name}'"
#             )
#             self.assertTrue(
#                 self.user.first_name != original_first_name,
#                 f"Expected first_name to change from '{original_first_name}', got '{self.user.first_name}'"
#             )
#         except Exception as e:
#             logger.error(f"Error verifying concurrent update: {e}", exc_info=True)
#             raise

#     def test_concurrent_user_delete(self):
#         """Test concurrent soft deletion and update of a user record."""
#         logger.info(f"Starting concurrent delete test for user: {self.user.username}")

#         def soft_delete_user(user_id, retries=3, retry_delay=0.5):
#             logger.debug(f"Thread soft deleting user id={user_id}")
#             for attempt in range(retries):
#                 try:
#                     with transaction.atomic():
#                         user = User.objects.select_for_update().get(id=user_id)
#                         user.soft_delete(user=user)
#                         logger.info(f"User id={user_id} soft deleted")
#                         break
#                 except ObjectDoesNotExist:
#                     logger.warning(f"User id={user_id} not found for delete on attempt {attempt + 1}, retrying...")
#                     time.sleep(retry_delay)
#                     if attempt == retries - 1:
#                         logger.error(f"Failed to soft delete user id={user_id} after {retries} attempts")
#                         raise
#                 except Exception as e:
#                     logger.error(f"Error in soft_delete_user: {e}", exc_info=True)
#                     raise

#         def update_user_email(user_id, email, delay=0.2, retries=3, retry_delay=0.5):
#             logger.debug(f"Thread updating user id={user_id} with email={email}")
#             for attempt in range(retries):
#                 try:
#                     with transaction.atomic():
#                         user = User.objects.select_for_update().get(id=user_id)
#                         time.sleep(delay)
#                         user.email = email
#                         user.save(user=user)
#                         logger.info(f"User id={user_id} updated with email={email}")
#                         break
#                 except ObjectDoesNotExist:
#                     logger.warning(f"User id={user_id} not found for update on attempt {attempt + 1}, retrying...")
#                     time.sleep(retry_delay)
#                     if attempt == retries - 1:
#                         logger.warning(f"User id={user_id} not found for update after {retries} attempts, skipping")
#                         break
#                 except Exception as e:
#                     logger.error(f"Error in update_user_email: {e}", exc_info=True)
#                     raise

#         thread1 = threading.Thread(target=soft_delete_user, args=(self.user.id,))
#         thread2 = threading.Thread(
#             target=update_user_email,
#             args=(self.user.id, 'newemail@example.com', 0.2)
#         )

#         logger.debug("Starting concurrent delete and update threads")
#         thread1.start()
#         thread2.start()
#         thread1.join()
#         thread2.join()

#         try:
#             self.user.refresh_from_db()
#             logger.info(f"User after concurrent delete/update: deleted_at={self.user.deleted_at}, email={self.user.email}")
#             self.assertIsNotNone(
#                 self.user.deleted_at,
#                 f"Expected deleted_at to be set, got None"
#             )
#             self.assertTrue(
#                 self.user.email in ('test@example.com', 'newemail@example.com'),
#                 f"Expected email to be 'test@example.com' or 'newemail@example.com', got '{self.user.email}'"
#             )
#         except Exception as e:
#             logger.error(f"Error verifying concurrent delete: {e}", exc_info=True)
#             raise
