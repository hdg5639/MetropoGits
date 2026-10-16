import org.springframework.data.mongodb.repository.MongoRepository;

class MongoStore {
    MongoRepository<Object, String> repository;
}
