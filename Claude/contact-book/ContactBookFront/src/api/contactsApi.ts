import client from './client';
import type { Contact, ContactRequest } from '../types/contact';

export const contactsApi = {
  list: () =>
    client.get<Contact[]>('/api/contacts').then((r) => r.data),

  get: (id: string) =>
    client.get<Contact>(`/api/contacts/${id}`).then((r) => r.data),

  create: (data: ContactRequest) =>
    client.post<Contact>('/api/contacts', data).then((r) => r.data),

  update: (id: string, data: ContactRequest) =>
    client.put<Contact>(`/api/contacts/${id}`, data).then((r) => r.data),

  remove: (id: string) =>
    client.delete(`/api/contacts/${id}`),
};
