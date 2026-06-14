package com.contactbook.web;

import com.contactbook.domain.Contact;
import com.contactbook.service.ContactNotFoundException;
import com.contactbook.service.ContactService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.net.URI;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Plain unit tests for {@link ContactController}. The controller is instantiated
 * directly with a mocked {@link ContactService} — no Spring context is loaded —
 * so these exercise only the controller's own behaviour: delegation to the
 * service, the 201/Location response from {@code create}, and that service
 * exceptions are allowed to propagate.
 *
 * <p>Routing, JSON (de)serialisation, {@code @Valid} validation and the
 * {@link GlobalExceptionHandler} status mapping are part of the Spring MVC layer
 * and are intentionally not covered here.</p>
 */
class ContactControllerTest {

    private final ContactService service = mock(ContactService.class);
    private final ContactController controller = new ContactController(service);

    @BeforeEach
    void bindRequest() {
        // create() builds the Location URI from the current request, which it
        // reads off RequestContextHolder; bind a fake request so that works.
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI("/api/contacts");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));
    }

    @AfterEach
    void clearRequest() {
        RequestContextHolder.resetRequestAttributes();
    }

    private static Contact sample(String id) {
        return new Contact(id, "Ada", "Lovelace",
                List.of("ada@example.com"), List.of("+381601234567"));
    }

    @Test
    void list_returnsAllContacts() {
        when(service.findAll()).thenReturn(List.of(sample("1"), sample("2")));

        List<Contact> result = controller.list();

        assertThat(result).hasSize(2);
        assertThat(result.get(0).id()).isEqualTo("1");
        assertThat(result.get(0).firstName()).isEqualTo("Ada");
    }

    @Test
    void get_returnsContact_whenFound() {
        when(service.findById("1")).thenReturn(sample("1"));

        Contact result = controller.get("1");

        assertThat(result.id()).isEqualTo("1");
        assertThat(result.emails()).containsExactly("ada@example.com");
    }

    @Test
    void get_propagatesNotFound_whenMissing() {
        when(service.findById("missing")).thenThrow(new ContactNotFoundException("missing"));

        assertThatThrownBy(() -> controller.get("missing"))
                .isInstanceOf(ContactNotFoundException.class)
                .hasMessage("Contact not found: missing");
    }

    @Test
    void create_returns201WithLocationAndBody() {
        Contact created = sample("generated-id");
        when(service.create(any(Contact.class))).thenReturn(created);

        ContactRequest request = new ContactRequest("Ada", "Lovelace",
                List.of("ada@example.com"), List.of("+381601234567"));

        ResponseEntity<Contact> response = controller.create(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        URI location = response.getHeaders().getLocation();
        assertThat(location).isNotNull();
        assertThat(location.toString()).endsWith("/api/contacts/generated-id");
        assertThat(response.getBody()).isEqualTo(created);
    }

    @Test
    void update_returnsUpdatedContact() {
        Contact updated = sample("1");
        when(service.update(eq("1"), any(Contact.class))).thenReturn(updated);

        ContactRequest request = new ContactRequest("Ada", "Lovelace",
                List.of("ada@example.com"), List.of("+381601234567"));

        Contact result = controller.update("1", request);

        assertThat(result.id()).isEqualTo("1");
    }

    @Test
    void update_propagatesNotFound_whenMissing() {
        when(service.update(eq("missing"), any(Contact.class)))
                .thenThrow(new ContactNotFoundException("missing"));

        ContactRequest request = new ContactRequest("Ada", "Lovelace",
                List.of("ada@example.com"), List.of());

        assertThatThrownBy(() -> controller.update("missing", request))
                .isInstanceOf(ContactNotFoundException.class);
    }

    @Test
    void delete_delegatesToService() {
        controller.delete("1");

        verify(service).delete("1");
    }

    @Test
    void delete_propagatesNotFound_whenMissing() {
        doThrow(new ContactNotFoundException("missing")).when(service).delete("missing");

        assertThatThrownBy(() -> controller.delete("missing"))
                .isInstanceOf(ContactNotFoundException.class);
    }
}
