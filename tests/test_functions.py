"""
Unit tests for client data functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from functions.client_notes import ClientNotesFunction
from functions.client_transactions import ClientTransactionsFunction


class TestClientNotes:

    @pytest.fixture
    def notes_function(self):
        return ClientNotesFunction()

    @pytest.fixture
    def mock_user_admin(self):
        return {
            'id': 'user123',
            'name': 'Test User',
            'role': 'admin'
        }

    @pytest.fixture
    def mock_user_unauthorized(self):
        return {
            'id': 'user456',
            'name': 'Unauthorized User',
            'role': 'readonly'
        }

    def test_permission_check_success(self, notes_function, mock_user_admin):
        """Test that admin can access notes"""
        result = notes_function._check_permissions(mock_user_admin, 'CLIENT123')
        assert result == True

    def test_permission_check_failure(self, notes_function, mock_user_unauthorized):
        """Test that unauthorized role is denied"""
        result = notes_function._check_permissions(mock_user_unauthorized, 'CLIENT123')
        assert result == False

    @patch.object(ClientNotesFunction, '_execute_query')
    @patch.object(ClientNotesFunction, '_check_permissions', return_value=True)
    def test_get_all_notes_success(self, mock_perms, mock_query, notes_function, mock_user_admin):
        """Test successful notes retrieval"""

        # Mock database results
        mock_query.return_value = [
            {
                'note_id': 1,
                'action_type': 'Call',
                'note_text': 'Called client',
                'created_by': 'John Doe',
                'created_date': '2025-01-15 10:00:00',
                'status': 'completed'
            }
        ]

        result = notes_function.get_all_notes('CLIENT123', __user__=mock_user_admin)

        assert '📋' in result
        assert 'CLIENT123' in result
        assert 'Call' in result

    @patch.object(ClientNotesFunction, '_check_permissions', return_value=False)
    def test_get_all_notes_permission_denied(self, mock_perms, notes_function, mock_user_unauthorized):
        """Test that unauthorized users get denied"""

        result = notes_function.get_all_notes('CLIENT123', __user__=mock_user_unauthorized)

        assert '🔒' in result
        assert 'Access denied' in result


class TestClientTransactions:

    @pytest.fixture
    def transactions_function(self):
        return ClientTransactionsFunction()

    @pytest.fixture
    def mock_user_finance(self):
        return {
            'id': 'user789',
            'name': 'Finance User',
            'role': 'finance'
        }

    @patch.object(ClientTransactionsFunction, '_execute_query')
    @patch.object(ClientTransactionsFunction, '_check_permissions', return_value=True)
    def test_get_transaction_count(self, mock_perms, mock_query, transactions_function, mock_user_finance):
        """Test transaction count retrieval"""

        mock_query.return_value = [{'transaction_count': 42}]

        result = transactions_function.get_transaction_count('CLIENT123', __user__=mock_user_finance)

        assert '💳' in result
        assert '42' in result
        assert 'CLIENT123' in result


# Run tests with:
# pytest tests/test_functions.py -v
