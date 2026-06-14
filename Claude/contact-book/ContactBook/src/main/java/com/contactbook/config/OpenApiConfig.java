package com.contactbook.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Meta podaci OpenAPI dokumentacije (naslov, verzija, opis). */
@Configuration
public class OpenApiConfig {

  @Bean
  public OpenAPI contactBookOpenApi() {
    return new OpenAPI()
        .info(
            new Info()
                .title("Contact Book API")
                .version("0.0.1")
                .description("REST API za upravljanje kontaktima (CRUD)."));
  }
}
