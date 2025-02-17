# API Load Testing with JMeter

This directory contains JMeter test plans for load testing the API Management Service endpoints.

## Test Plans

1. `products_api_test.jmx` - Load tests for Products API endpoints
2. `orders_api_test.jmx` - Load tests for Orders API endpoints

## Test Scenarios

### Common Configuration for Both Test Plans

- Concurrent Users: 10, 50, and 100 users
- Ramp-up Period: 30 seconds
- Test Duration: 5 minutes
- Think Time: 1-3 seconds between requests
- Performance Assertions:
  - Response time < 500ms (90th percentile)
  - Error rate < 1%
  - Throughput >= 100 requests/second

### Products API Test Scenarios

1. List Products (GET /products)
2. Get Product by ID (GET /products/{id})
3. Create Product (POST /products)
4. Update Product (PUT /products/{id})
5. Delete Product (DELETE /products/{id})

### Orders API Test Scenarios

1. List Orders (GET /orders)
2. Get Order by ID (GET /orders/{id})
3. Create Order (POST /orders)
4. Update Order Status (PUT /orders/{id})
5. Delete Order (DELETE /orders/{id})

## Special Test Scenarios

1. Cache Hit/Miss Verification
2. Rate Limiting Threshold Testing
3. Database Connection Pool Saturation Test

## Running the Tests

1. Install Apache JMeter
2. Start the API Management Service
3. Open JMeter and load the desired test plan (.jmx file)
4. Configure the following variables if needed:
   - HOST (default: localhost)
   - PORT (default: 8000)
   - PROTOCOL (default: http)
5. Run the test plan

## Viewing Results

The test plans include two result listeners:
1. View Results Tree - For detailed request/response data
2. Summary Report - For aggregate performance metrics

## Best Practices

1. Clear JMeter's result cache before each test run
2. Ensure the API service is in a clean state before testing
3. Monitor server resources during test execution
4. Save test results for comparison and analysis

## Notes

- The test plans include think time between requests to simulate real user behavior
- Response assertions are configured to verify successful responses
- Tests are configured to run for 5 minutes to ensure steady-state performance