from fastapi import APIRouter, Depends

tickets_router = APIRouter()

@tickets_router.get("/")
def get_tickets():
    print('hello')