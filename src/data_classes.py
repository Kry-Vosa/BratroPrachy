from dataclasses import dataclass

@dataclass(order = True, frozen = True)
class CustomerInfo:
    customer_id: int
    first_name: str
    last_name: str
    nickname: str
    balance: int
    