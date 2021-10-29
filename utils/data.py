from typing import Optional
from beancount.core.data import Posting, Transaction


class Data:
    pending_entries = dict()
    default_account = "TODO: store in config"
    fixme_account = "TODO: store in config"
    transactions = {}

    def __init__(self) -> None:
        self.get_all_transactions()

    def prepare_entries_to_import(self, pending: list):
        self.pending_entries.clear()
        entry: ImportResult
        for i, entry in enumerate(pending):
            self.pending_entries[i] = entry

    def format_entries(self) -> str:
        entry: ImportResult
        return "".join(
            self.create_entry_from_import_result(entry)
            for entry in self.pending_entries.values()
        )

    def create_entry_from_import_result(self, entry: ImportResult) -> str:
        e: Transaction = entry.entries[0]
        return '{} * "{}"\n\
                {}  {}\n\
                {}  {}\n\n'.format(
            entry.date,
            e.narration,
            e.postings[0].account,
            e.postings[0].units.to_string(),
            e.postings[1].account,
            e.postings[1].units.to_string(),
        )

    def create_transaction_entry_from_import_result(self, entry: ImportResult) -> str:
        e: Transaction = entry.entries[0]
        return '{} * {}"{}"\n\
      {}  {}\n\
        date: {}\n\
        source_desc: "{}"\n\
      {}  {}\n\n'.format(
            entry.date,
            "" if e.payee is None else '"{}" '.format(e.payee),
            e.narration,
            e.postings[0].account,
            e.postings[0].units.to_string(),
            entry.date,
            e.narration,
            e.postings[1].account,
            e.postings[1].units.to_string(),
        )

    def propose_account(self, narration: str) -> Optional[str]:
        if narration in account_mapping:
            return account_mapping[narration]
        if narration in self.transactions:
            acc = set()
            transaction: Transaction
            for transaction in self.transactions[narration]:
                posting: Posting
                for posting in transaction.postings:
                    if posting.account != self.default_account:
                        acc.add(posting.account)
            if len(acc) == 1:
                return acc.pop()
        return None

    def get_all_transactions(self):
        for entry in journal.all_entries:
            if isinstance(entry, Transaction):
                n = entry.narration
                p = entry.payee
                if n not in self.transactions:
                    self.transactions[n] = []
                self.transactions[n].append(entry)
