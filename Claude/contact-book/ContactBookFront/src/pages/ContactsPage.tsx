import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { contactsApi } from '../api/contactsApi';
import type { Contact } from '../types/contact';
import ContactCard from '../components/ContactCard';
import ConfirmDialog from '../components/ConfirmDialog';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<Contact | null>(null);

  useEffect(() => {
    contactsApi
      .list()
      .then(setContacts)
      .catch(() => setError('Failed to load contacts.'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = contacts.filter((c) =>
    `${c.firstName} ${c.lastName}`.toLowerCase().includes(search.toLowerCase())
  );

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await contactsApi.remove(deleteTarget.id);
      setContacts((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      setError('Failed to delete contact.');
      setDeleteTarget(null);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search contacts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
        </div>
        <Link
          to="/contacts/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Contact
        </Link>
      </div>

      {error && <div className="mb-4"><ErrorMessage message={error} /></div>}
      {loading && <LoadingSpinner />}

      {!loading && !error && filtered.length === 0 && (
        <div className="text-center py-16 text-gray-400 dark:text-slate-500">
          {search
            ? `No contacts matching "${search}"`
            : 'No contacts yet. Add your first one!'}
        </div>
      )}

      {!loading && (
        <div className="grid gap-3 sm:grid-cols-2">
          {filtered.map((contact) => (
            <ContactCard
              key={contact.id}
              contact={contact}
              onDeleteClick={setDeleteTarget}
            />
          ))}
        </div>
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Delete Contact"
          message={`Are you sure you want to delete ${deleteTarget.firstName} ${deleteTarget.lastName}?`}
          onConfirm={handleConfirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
