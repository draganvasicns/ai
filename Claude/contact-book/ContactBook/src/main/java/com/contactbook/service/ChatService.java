package com.contactbook.service;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.contactbook.config.AnthropicProperties;
import com.contactbook.web.ChatMessage;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class ChatService {

  private final AnthropicClient client;
  private final AnthropicProperties props;

  public ChatService(AnthropicProperties props) {
    this.props = props;
    this.client = AnthropicOkHttpClient.builder().apiKey(props.apiKey()).build();
  }

  public String chat(List<ChatMessage> messages) {
    var builder =
        MessageCreateParams.builder().model(Model.of(props.model())).maxTokens(props.maxTokens());

    for (ChatMessage msg : messages) {
      if ("user".equals(msg.role())) {
        builder.addUserMessage(msg.content());
      } else {
        builder.addAssistantMessage(msg.content());
      }
    }

    var response = client.messages().create(builder.build());
    return response.content().get(0).asText().text();
  }
}
