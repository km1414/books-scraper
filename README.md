# Books Scraper

Application for scraping [Books to Scrape](https://books.toscrape.com/) with 2 services:
- **scraper** - asynchronous page scraping, jobs scheduling
- **parser** - data parsing, transformation, validation and saving

Build and run locally with Docker Compose:
```
docker-compose up --build
```

Run with [MiniKube](https://minikube.sigs.k8s.io/docs/start/), [Kind](https://kind.sigs.k8s.io/docs/user/quick-start/), etc.:
```
kubectl apply -f ./k8s

# check the logs
kubectl logs -f deployment/scraper-deployment
kubectl logs -f deployment/parser-deployment
```

### TODO:

- [x] Scraping application
- [x] gRPC service for data parsing/storing
- [x] Containerization
- [x] K8s deployment manifests
- [x] Documentation
- [ ] Unit tests
- [ ] Code structure improvements
- [ ] Error handling/logging improvements
- [ ] Data storage to DB
- [ ] Reuse single Docker image

### Possible issues:

- Any change in page structure would possibly break the application
- Data inconsistency of single book would compromise whole run - no books would be updated
