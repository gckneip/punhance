from src.domain.entities.account import AccountType
from src.domain.entities.purchase import PaymentMethod

# HomeBank account type codes -> our AccountType. Code 4 (creditcard) is
# handled separately since it maps to our CreditCard entity, not Account.
HB_ACCOUNT_TYPE_TO_OURS = {
    0: AccountType.CASH,
    1: AccountType.CHECKING,
    2: AccountType.CASH,
    3: AccountType.INVESTMENT,
    5: AccountType.CHECKING,
}
HB_ACCOUNT_TYPE_CREDITCARD = 4

OUR_ACCOUNT_TYPE_TO_HB = {
    AccountType.CHECKING: 1,
    AccountType.SAVINGS: 1,
    AccountType.CASH: 2,
    AccountType.VOUCHER: 2,
    AccountType.INVESTMENT: 3,
}

# HomeBank paymode codes -> our PaymentMethod (only consulted for rows that
# become a Purchase: splits, or any row against a credit-card account).
HB_PAYMODE_TO_PAYMENT_METHOD = {
    0: PaymentMethod.CASH,
    1: PaymentMethod.CREDIT_CARD,
    2: PaymentMethod.BANK_TRANSFER,
    3: PaymentMethod.CASH,
    4: PaymentMethod.BANK_TRANSFER,
    6: PaymentMethod.DEBIT_CARD,
    7: PaymentMethod.BANK_TRANSFER,
    8: PaymentMethod.BANK_TRANSFER,
    9: PaymentMethod.BANK_TRANSFER,
    10: PaymentMethod.BANK_TRANSFER,
    11: PaymentMethod.BANK_TRANSFER,
}
HB_PAYMODE_INTERNAL_TRANSFER = 5

PAYMENT_METHOD_TO_HB_PAYMODE = {
    PaymentMethod.CREDIT_CARD: 1,
    PaymentMethod.DEBIT_CARD: 6,
    PaymentMethod.CASH: 3,
    PaymentMethod.BANK_TRANSFER: 4,
    PaymentMethod.PIX: 8,
}

HB_PAYMODE_TRANSFER = HB_PAYMODE_INTERNAL_TRANSFER
