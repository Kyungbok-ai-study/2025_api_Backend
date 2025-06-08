from qdrant_client import QdrantClient

qdrant_client = QdrantClient(
    url="https://c5af819b-eb1c-45b9-b5db-a5d458d03d9d.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.mtR5MB8F35kIuu2KCh5uA2dlO_SRBlb0mBMDdiyneWk",
)

print(qdrant_client.get_collections())