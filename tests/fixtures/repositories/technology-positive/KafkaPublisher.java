import org.springframework.kafka.core.KafkaTemplate;

class KafkaPublisher {
    KafkaTemplate<String, String> template;
}
