from aiogram.filters.callback_data import CallbackData


class RemoveItemCallback(CallbackData, prefix="remove"):
    item_id: int


class GetItemCallback(CallbackData, prefix="item"):
    item_id: int
