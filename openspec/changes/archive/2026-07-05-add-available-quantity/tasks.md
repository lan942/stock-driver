## 1. Backend — Add available_quantity to get_holdings

- [x] 1.1 In `get_holdings()` in [portfolio_service.py](file:///d:/stock-driver/backend/services/portfolio_service.py), query today's buy transactions grouped by code to get `today_buy_quantity` for each holding
- [x] 1.2 Add `available_quantity` field to the response dict in `get_holdings()`, calculated as `quantity - today_buy_quantity`

## 2. Frontend — Add available quantity column to holdings table

- [x] 2.1 Add "可用数量" column to the holdings table in [Portfolio.vue](file:///d:/stock-driver/frontend/src/views/Portfolio.vue), positioned after the "持仓数量" column
- [x] 2.2 Style unavailable quantity (holdings where available < quantity) to visually indicate T+1 restriction (e.g., red/orange text)