import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { contactsApi } from '../api/contactsApi';
import type { Contact } from '../types/contact';
import ConfirmDialog from '../components/ConfirmDialog';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

export default function ContactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    if (!id) return;
    contactsApi
      .get(id)
      .then(setContact)
      .catch(() => setError('Contact not found.'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!id) return;
    try {
      await contactsApi.remove(id);
      navigate('/contacts');
    } catch {
      setError('Failed to delete contact.');
      setShowConfirm(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <Link
          to="/contacts"
          className="inline-flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Contacts
        </Link>
      </div>

      {error && <div className="mb-4"><ErrorMessage message={error} /></div>}
      {loading && <LoadingSpinner />}

      {contact && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6">
          <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-blue-600 text-white flex items-center justify-center text-2xl font-bold select-none flex-shrink-0">
                {contact.firstName.charAt(0)}{contact.lastName.charAt(0)}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-100">
                {contact.firstName} {contact.lastName}
              </h2>
            </div>
            <div className="flex gap-2">
              <Link
                to={`/contacts/${contact.id}/edit`}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 border border-blue-600 dark:border-blue-400 rounded-lg hover:bg-blue-50 dark:hover:bg-slate-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
                Edit
              </Link>
              <button
                onClick={() => setShowConfirm(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-500 rounded-lg hover:bg-red-600 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                Delete
              </button>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            {(contact.emails?.length ?? 0) > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-3">
                  Email Addresses
                </h3>
                <ul className="space-y-2">
                  {(contact.emails ?? []).map((email, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300">
                      <svg
                        className="w-4 h-4 text-blue-400 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                        />
                      </svg>
                      <a
                        href={`mailto:${email}`}
                        className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      >
                        {email}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(contact.phoneNumbers?.length ?? 0) > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-3">
                  Phone Numbers
                </h3>
                <ul className="space-y-2">
                  {(contact.phoneNumbers ?? []).map((phone, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300">
                      <svg
                        className="w-4 h-4 text-blue-400 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.948V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                        />
                      </svg>
                      <a
                        href={`tel:${phone}`}
                        className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      >
                        {phone}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(contact.emails?.length ?? 0) === 0 && (contact.phoneNumbers?.length ?? 0) === 0 && (
              <p className="text-sm text-gray-400 dark:text-slate-500 col-span-2">No contact details available.</p>
            )}
          </div>
        </div>
      )}

      {showConfirm && contact && (
        <ConfirmDialog
          title="Delete Contact"
          message={`Are you sure you want to delete ${contact.firstName} ${contact.lastName}? This action cannot be undone.`}
          onConfirm={handleDelete}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </div>
  );
}
