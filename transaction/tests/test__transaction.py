##############################################################################
#
# Copyright (c) 2001, 2002, 2005 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Test transaction behavior for variety of cases.

I wrote these unittests to investigate some odd transaction
behavior when doing unittests of integrating non sub transaction
aware objects, and to insure proper txn behavior. these
tests test the transaction system independent of the rest of the
zodb.

you can see the method calls to a jar by passing the
keyword arg tracing to the modify method of a dataobject.
the value of the arg is a prefix used for tracing print calls
to that objects jar.

the number of times a jar method was called can be inspected
by looking at an attribute of the jar that is the method
name prefixed with a c (count/check).

i've included some tracing examples for tests that i thought
were illuminating as doc strings below.

TODO

    add in tests for objects which are modified multiple times,
    for example an object that gets modified in multiple sub txns.
"""
import unittest


class TransactionTests(unittest.TestCase):

    def _getTargetClass(self):
        from transaction._transaction import Transaction
        return Transaction

    def _makeOne(self, synchronizers=None, manager=None):
        return self._getTargetClass()(synchronizers, manager)

    def test_note(self):
        t = self._makeOne()
        try:
            t.note('This is a note.')
            self.assertEqual(t.description, 'This is a note.')
            t.note('Another.')
            self.assertEqual(t.description, 'This is a note.\nAnother.')
        finally:
            t.abort()


class Test_oid_repr(unittest.TestCase):

    def _callFUT(self, oid):
        from transaction._transaction import oid_repr
        return oid_repr(oid)

    def test_as_nonstring(self):
        self.assertEqual(self._callFUT(123), '123')

    def test_as_string_not_8_chars(self):
        self.assertEqual(self._callFUT('a'), "'a'")

    def test_as_string_z64(self):
        s = '\0'*8
        self.assertEqual(self._callFUT(s), '0x00')

    def test_as_string_all_Fs(self):
        s = '\1'*8
        self.assertEqual(self._callFUT(s), '0x0101010101010101')


class MiscellaneousTests(unittest.TestCase):

    def test_BBB_join(self):
        # The join method is provided for "backward-compatability" with ZODB 4
        # data managers.
        from transaction import Transaction
        from transaction.tests.examples import DataManager
        from transaction._transaction import DataManagerAdapter
        # The argument to join must be a zodb4 data manager,
        # transaction.interfaces.IDataManager.
        t = Transaction()
        dm = DataManager()
        t.join(dm)
        # The end result is that a data manager adapter is one of the
        # transaction's objects:
        self.assertTrue(isinstance(t._resources[0], DataManagerAdapter))
        self.assertTrue(t._resources[0]._datamanager is dm)

    def test_bug239086(self):
        # The original implementation of thread transaction manager made
        # invalid assumptions about thread ids.
        import threading
        import transaction
        import transaction.tests.savepointsample as SPS
        dm = SPS.SampleSavepointDataManager()
        self.assertEqual(list(dm.keys()), [])

        class Sync:
             def __init__(self, label):
                 self.label = label
                 self.log = []
             def beforeCompletion(self, t):
                 self.log.append('%s %s' % (self.label, 'before'))
             def afterCompletion(self, t):
                 self.log.append('%s %s' % (self.label, 'after'))
             def newTransaction(self, t):
                 self.log.append('%s %s' % (self.label, 'new'))

        def run_in_thread(f):
            t = threading.Thread(target=f)
            t.start()
            t.join()

        sync = Sync(1)
        @run_in_thread
        def first():
            transaction.manager.registerSynch(sync)
            transaction.manager.begin()
            dm['a'] = 1
        self.assertEqual(sync.log, ['1 new'])

        @run_in_thread
        def second():
            transaction.abort() # should do nothing.
        self.assertEqual(sync.log, ['1 new'])
        self.assertEqual(list(dm.keys()), ['a'])

        dm = SPS.SampleSavepointDataManager()
        self.assertEqual(list(dm.keys()), [])

        @run_in_thread
        def third():
            dm['a'] = 1
        self.assertEqual(sync.log, ['1 new'])

        transaction.abort() # should do nothing
        self.assertEqual(list(dm.keys()), ['a'])


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TransactionTests),
        unittest.makeSuite(Test_oid_repr),
        unittest.makeSuite(MiscellaneousTests),
        ))