# Cars Dealership Review Portal

Cars Dealership is a national retailer directory and review portal. Search branches by state, browse dealer reviews, and sign in to post a review. React provides the interface, Django manages authentication and the SQLite vehicle catalog, Express and MongoDB store branches and reviews, and Flask rates review sentiment.

The GitHub Actions workflow builds the frontend, starts MongoDB and the three services, verifies the API with cURL, and captures browser evidence. It uses the official IBM starter data. The evidence is from the CI environment.
