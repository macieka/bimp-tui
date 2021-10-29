import collections
import datetime
from typing import AbstractSet, Callable, Dict, Iterable, List, Tuple

from beancount.core.data import Directive, Open, Posting, Transaction
from beancount_import import journal_editor
from beancount_import.source import SourceResults
from beancount_import.source.description_based_source import (
    RawEntry, RawEntryKey, get_posting_source_descs)
from beancount_import.unbook import group_postings_by_meta, unbook_postings


class Journal:
    def __init__(self) -> None:
        journal_input = "TODO: store in config"
        ignored_journal = "TODO: store in config"
        self.journal = journal_editor.JournalEditor(journal_input, ignored_journal)
        self.account_to_mint_id, self.mint_id_to_account = self.get_account_mapping(
            self.journal.accounts, "account_id"
        )

    def get_account_mapping(
        self, accounts: Dict[str, Open], metadata_key: str
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Populates the bidirectional mappings id_to_account and
        account_to_id based on the metadata_key metadata field.
        """

        id_to_account = {}  # type: Dict[str, str]
        account_to_id = {}  # type: Dict[str, str]

        for entry in accounts.values():
            account_id = entry.meta.get(metadata_key, None)
            if account_id is None:
                continue
            if not isinstance(account_id, str):
                raise RuntimeError(
                    "Invalid %s (not string): %r" % (metadata_key, account_id)
                )
            if "," in account_id:
                accounts = account_id.split(",")
                for a in accounts:
                    account_to_id[entry.account] = a
                    id_to_account[a] = entry.account
            else:
                account_to_id[entry.account] = account_id
                id_to_account[account_id] = entry.account
            account_to_id[entry.account] = account_id
            id_to_account[account_id] = entry.account
        return account_to_id, id_to_account

    def get_pending_and_invalid_entries(
        self,
        raw_entries: Iterable[RawEntry],
        journal_entries: Iterable[Directive],
        account_set: AbstractSet[str],
        get_key_from_posting: Callable[
            [Transaction, Posting, List[Posting], str, datetime.date], RawEntryKey
        ],
        get_key_from_raw_entry: Callable[[RawEntry], RawEntryKey],
        make_import_result: Callable[[RawEntry], Transaction],
        results: SourceResults,
    ) -> None:
        matched_postings = (
            dict()
        )  # type: Dict[RawEntryKey, List[Tuple[Transaction, Posting]]]

        for entry in journal_entries:
            if not isinstance(entry, Transaction):
                continue
            for postings in group_postings_by_meta(entry.postings):
                posting = unbook_postings(postings)
                if posting.meta is None:
                    continue
                if posting.account not in account_set:
                    continue
                for source_desc, posting_date in get_posting_source_descs(posting):
                    key = get_key_from_posting(
                        entry, posting, postings, source_desc, posting_date
                    )
                    if key is None:
                        continue
                    matched_postings.setdefault(key, []).append((entry, posting))

        matched_postings_counter = collections.Counter()  # type: Dict[RawEntryKey, int]
        for key, entry_posting_pairs in matched_postings.items():
            matched_postings_counter[key] += len(entry_posting_pairs)

        temp_pending_entries = {}
        temp_pending_entries_short = {}
        for raw_entry in raw_entries:
            key = get_key_from_raw_entry(raw_entry)
            if matched_postings_counter[key] > 0:
                matched_postings_counter[key] -= 1
            else:
                temp_pending_entries_short[
                    self._get_short_key_from_csv(raw_entry)
                ] = raw_entry
                temp_pending_entries[key] = raw_entry
                results.add_pending_entry(make_import_result(raw_entry))

        results.add_accounts(account_set)

    @staticmethod
    def _get_short_key_from_csv(x: MbankEntry):
        return x.account, x.date, x.amount
