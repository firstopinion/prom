# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import datetime
import time
from threading import Thread
import sys

import testdata
#from testdata.threading import Thread

from . import BaseTestCase, EnvironTestCase, TestCase, SkipTest
from prom.query import (
    Query,
    Bounds,
    Field,
    Fields,
    CacheQuery,
    Iterator,
    AllIterator,
)
from prom.compat import *
import prom


class FieldTest(BaseTestCase):
    def test___new__(self):
        q = self.get_query()
        f = Field(q, "MAX(foo)")
        #f = Field("MAX(foo)", schema=testdata.mock(field_name="foo"))
        self.assertEqual("foo", f.name)
        self.assertEqual("MAX", f.function_name)


class FieldsTest(BaseTestCase):
    def test_fields(self):
        q = self.get_query()
        fs = Fields()
        fs.append(Field(q, "foo", 1))
        fs.append(Field(q, "foo", 2))
        fs.append(Field(q, "bar", 3))
        #fs.append(Field(q, "che", 4))

        fields = fs.fields
        self.assertEqual(2, fields["foo"])
        self.assertEqual(3, fields["bar"])
        #self.assertEqual(4, fields["che"])

    def test___bool__(self):
        fs = Fields()
        self.assertFalse(fs)

        q = self.get_query()
        fs.append(Field(q, "foo", 1))
        self.assertTrue(fs)






#     def test___missing__(self):
#         fs = Fields()
#         fs["foo"] = ["foo", 1]
#         self.assertTrue("foo" in fs)
# 
#     def test___contains__(self):
#         fs = Fields()
#         fs.append("foo", ["foo", 1])
#         fs.append("foo", ["foo", 2])
#         self.assertTrue("foo" in fs)
#         self.assertFalse("bar" in fs)
# 
#     def test_get(self):
#         fs = Fields()
#         fs.append("foo", ["foo", 1])
#         self.assertEqual(1, len(fs.get("foo")))
# 
#         fs.append("foo", ["foo", 2])
#         self.assertEqual(2, len(fs.get("foo")))
# 
#         fs.append("bar", ["bar", "one"])
#         self.assertEqual(1, len(fs.get("bar")))
#         self.assertEqual(1, len(fs.get("bar")))
#         self.assertEqual(2, len(fs.get("foo")))


class BoundsTest(TestCase):
    def test___nonzero__(self):
        b = Bounds()

        self.assertFalse(b)

    def test_offset_from_page(self):
        lc = Bounds()
        lc.page = 2
        self.assertEqual(1, lc.offset)

        lc = Bounds()
        lc.limit = 5
        lc.page = 2
        self.assertEqual(5, lc.offset)
        self.assertEqual(5, lc.limit)

    def test_non_paginate_limit(self):
        lc = Bounds()

        self.assertEqual((0, 0), lc.get())

        lc.limit = 10

        self.assertEqual((10, 0), lc.get())

        lc.page = 1
        self.assertEqual((10, 0), lc.get())

        lc.offset = 15
        self.assertEqual((10, 15), lc.get())

        lc.page = 2
        self.assertEqual((10, 10), lc.get())

        lc.page = 3
        self.assertEqual((10, 20), lc.get())

        lc.page = 0
        self.assertEqual((10, 0), lc.get())

        with self.assertRaises(ValueError):
            lc.page = -10

        lc.offset = 0
        self.assertEqual((10, 0), lc.get())

        with self.assertRaises(ValueError):
            lc.offset = -10

        lc.limit = 0
        self.assertEqual((0, 0), lc.get())

        with self.assertRaises(ValueError):
            lc.limit = -10

    def test_paginate_limit(self):
        lc = Bounds()

        lc.limit = 10
        lc.paginate = True
        self.assertEqual(11, lc.limit)
        self.assertEqual((11, 0), lc.get())

        lc.page = 3
        self.assertEqual((11, 20), lc.get())

        lc.offset = 15
        self.assertEqual((11, 15), lc.get())

        lc.paginate = False
        self.assertEqual((10, 15), lc.get())


class QueryTest(EnvironTestCase):
#     @classmethod
#     def setUpClass(cls):
#         from unittest import SkipTest
#         raise SkipTest()

    def test_render(self):
        q = self.get_query()

        q.is_foo(1)
        q.is_bar("two")
        r = q.render()
        self.assertRegex(r, r"foo[^=]+=\s*1")
        self.assertRegex(r, r"bar[^=]+=\s*'two'")

    def test_find_operation_method_1(self):
        q = self.get_query()

        opm, fn = q.find_operation_method("eq_foo_bar")
        opm2, fn2 = q.find_operation_method("foo_bar_eq")
        self.assertEqual("eq_field", opm.__name__)
        self.assertEqual(opm2.__name__, opm.__name__)
        self.assertEqual("foo_bar", fn)
        self.assertEqual(fn2, fn)

        with self.assertRaises(AttributeError):
            q.find_operation_method("baklsdkf_foo_bar")

        with self.assertRaises(AttributeError):
            q.find_operation_method("baklsdkf_field")

        with self.assertRaises(AttributeError):
            q.find_operation_method("_field")

        with self.assertRaises(AttributeError):
            q.find_operation_method("baklsdkf")

    def test_find_operation_method_2(self):
        q = self.get_query()

        method_name = "is_{}".format(testdata.random.choice(list(q.schema.fields.keys())))
        r = q.find_operation_method(method_name)
        self.assertEqual("is_field", r[0].__name__)
        self.assertTrue(r[1] in set(q.schema.fields.keys()))

        with self.assertRaises(AttributeError):
            q.find_operation_method("testing")

        q = self.get_query()
        q.orm_class = None
        tests = [
            ("gt_foo_bar", ("gt_field", "foo_bar")),
        ]

        for t in tests:
            r = q.find_operation_method(t[0])
            self.assertEqual(t[1][0], r[0].__name__)
            self.assertEqual(t[1][1], r[1])

    def test_like(self):
        _q = self.get_query()
        self.insert(_q, 5)
        for bar in ["bar che", "foo bar", "foo bar che"]:
            self.insert_fields(_q, bar=bar)

        count = _q.copy().like_bar("bar%").count()
        self.assertEqual(1, count)

        count = _q.copy().like_bar("%bar").count()
        self.assertEqual(1, count)

        count = _q.copy().like_bar("%bar%").count()
        self.assertEqual(3, count)

        count = _q.copy().nlike_bar("bar%").count()
        self.assertEqual(7, count)

        count = _q.copy().nlike_bar("%bar").count()
        self.assertEqual(7, count)

        count = _q.copy().nlike_bar("%bar%").count()
        self.assertEqual(5, count)

        count = _q.copy().like_bar("bar____").count()
        self.assertEqual(1, count)

        count = _q.copy().like_bar("____bar").count()
        self.assertEqual(1, count)

        count = _q.copy().like_bar("____bar____").count()
        self.assertEqual(1, count)

    def test_between(self):
        _q = self.get_query()
        self.insert(_q, 5)

        q = _q.copy()
        vals = list(q.between_pk(2, 4).pks())
        self.assertEqual(3, len(vals))
        for v in vals:
            self.assertTrue(v >= 2 and v <= 4)

    def test_ref_threading(self):
        basedir = testdata.create_modules({
            "rtfoo.rtbar.tqr1": [
                "import prom",
                "",
                "class Foo(prom.Orm):",
                "    table_name = 'thrd_qr2_foo'",
                "    one=prom.Field(int, True)",
                "",
            ],
            "rtfoo.rtbar.tqr2": [
                "import prom",
                "from tqr1 import Foo",
                "",
                "class Bar(prom.Orm):",
                "    table_name = 'thrd_qr2_bar'",
                "    one=prom.Field(int, True)",
                "    foo_id=prom.Field(Foo, True)",
                ""
            ]
        })

        tqr1 = basedir.module("rtfoo.rtbar.tqr1")
        sys.modules.pop("rtfoo.rtbar.tqr2.Bar", None)
        #tqr2 = basedir.module("tqr2")
        def target():
            q = tqr1.Foo.query.ref("rtfoo.rtbar.tqr2.Bar")
            f = tqr1.Foo()
            q = f.query.ref("rtfoo.rtbar.tqr2.Bar")

        t1 = Thread(target=target)
        # if we don't get stuck in a deadlock this test passes
        t1.start()
        t1.join()

    def test_query_ref_1(self):
        testdata.create_modules({
            "qr2": "\n".join([
                "import prom",
                "",
                "class Foo(prom.Orm):",
                "    table_name = 'qr2_foo'",
                "    foo=prom.Field(int, True)",
                "    bar=prom.Field(str, True)",
                ""
                "class Bar(prom.Orm):",
                "    table_name = 'qr2_bar'",
                "    foo=prom.Field(int, True)",
                "    bar=prom.Field(str, True)",
                "    che=prom.Field(Foo, True)",
                ""
            ])
        })

        from qr2 import Foo as t1, Bar as t2

        ti1 = t1.create(foo=11, bar='11')
        ti12 = t1.create(foo=12, bar='12')

        ti2 = t2.create(foo=21, bar='21', che=ti1.pk)
        ti22 = t2.create(foo=22, bar='22', che=ti12.pk)

        orm_classpath = "{}.{}".format(t2.__module__, t2.__name__)

        l = list(ti1.query.ref(orm_classpath).select_foo().is_pk(ti12.pk).values())
        self.assertEqual(22, l[0])
        self.assertEqual(1, len(l))

        l = list(ti1.query.ref(orm_classpath).select_foo().is_pk(ti1.pk).all().values())
        self.assertEqual(21, l[0])
        self.assertEqual(1, len(l))

        l = list(ti1.query.ref(orm_classpath).select_foo().is_pk(ti1.pk).get().values())
        self.assertEqual(21, l[0])
        self.assertEqual(1, len(l))

        l = list(ti1.query.ref(orm_classpath).select_foo().is_pk(ti1.pk).values())
        self.assertEqual(21, l[0])
        self.assertEqual(1, len(l))

        l = list(ti1.query.ref(orm_classpath).select_foo().all().values())
        self.assertEqual(2, len(l))

    def test_query_ref_2(self):
        testdata.create_modules({
            "qre": "\n".join([
                "import prom",
                "",
                "class T1(prom.Orm):",
                "    table_name = 'qre_t1'",
                ""
                "class T2(prom.Orm):",
                "    table_name = 'qre_t2'",
                "    t1_id=prom.Field(T1, True)",
                ""
                "class T3(prom.Orm):",
                "    table_name = 'qre_t3'",
                ""
            ])
        })

        from qre import T1, T2, T3

        t1a = T1.create()
        t1b = T1.create()
        t2 = T2.create(t1_id=t1a.pk)

        classpath = "{}.{}".format(T2.__module__, T2.__name__)

        r = T1.query.ref(classpath).is_pk(t1a.pk).count()
        self.assertEqual(1, r)

        r = T1.query.ref(classpath).is_pk(t1b.pk).count()
        self.assertEqual(0, r)

    def test_null_iterator(self):
        """you can now pass empty lists to in and nin and not have them throw an
        error, instead they return an empty iterator"""
        _q = self.get_query()
        self.insert(_q, 1)

        q = _q.copy()
        r = q.in_foo([]).get()
        self.assertFalse(r)
        count = 0
        for x in r:
            count += 0
        self.assertEqual(0, count)
        self.assertEqual(0, len(r))

    def test_field_datetime(self):
        _q = self.get_query()

        q = _q.copy()
        q.is__created(day=int(datetime.datetime.utcnow().strftime('%d')))
        r = q.get()
        self.assertFalse(r)

        pk = self.insert(q, 1)[0]

        # get the object out so we can use it to query
        o = _q.copy().get_pk(pk)
        dt = o._created
        day = int(dt.strftime('%d'))

        pout.b()
        q = _q.copy()
        q.in__created(day=day)
        r = q.get()
        self.assertEqual(1, len(r))
        return

        q = _q.copy()
        q.is__created(day=day)
        r = q.get()
        self.assertEqual(1, len(r))

        q = _q.copy()
        q.in__created(day=[day, day + 1])
        r = q.get()
        self.assertEqual(1, len(r))

    def test_pk_fields(self):
        tclass = self.get_orm_class()
        q = tclass.query
        q.gte_pk(5).lte_pk(1).lt_pk(1).gte_pk(5)
        q.desc_pk()
        q.asc_pk()
        q.set_pk(None)

        for where_field in q.fields_where:
            self.assertEqual(where_field.name, "_id")

        for sort_field in q.fields_sort:
            self.assertEqual(sort_field.name, "_id")

        for set_field in q.fields_set:
            self.assertEqual(set_field.name, "_id")

    def test_get_pks(self):
        tclass = self.get_orm_class()
        t = tclass()
        t.foo = 1
        t.bar = "bar1"
        t.save()

        t2 = tclass()
        t2.foo = 2
        t2.bar = "bar2"
        t2.save()

        pks = [t.pk, t2.pk]

        res = tclass.query.get_pks(pks)
        self.assertEqual(2, len(res))
        self.assertEqual(list(res.pk), pks)

    def test_value_query(self):
        _q = self.get_query()

        v = _q.copy().select_foo().value()
        self.assertEqual(None, v)

        count = 2
        pks = self.insert(_q, count)
        o = _q.copy().get_pk(pks[0])

        v = _q.copy().select_foo().is_pk(o.pk).value()
        self.assertEqual(o.foo, v)

        v = _q.copy().select_foo().select_bar().is_pk(o.pk).value()
        self.assertEqual(o.foo, v[0])
        self.assertEqual(o.bar, v[1])

    def test_values_query(self):
        _q = self.get_query()

        count = 2
        pks = self.insert(_q, count)

        vals = _q.copy().select_foo().values()
        self.assertEqual(count, len(vals))
        for v in vals:
            self.assertTrue(isinstance(v, int))

        vals = _q.copy().select_foo().select_bar().values()
        self.assertEqual(count, len(vals))
        for v in vals:
            self.assertTrue(isinstance(v, list))

        vals = _q.copy().select_foo().values(limit=1)
        self.assertEqual(1, len(vals))

    def test_pk(self):
        orm_class = self.get_orm_class()
        v = orm_class.query.pk()
        self.assertEqual(None, v)
        count = 2
        self.insert(orm_class, count)

        v = orm_class.query.asc_pk().pk()
        self.assertEqual(1, v)

    def test_pks(self):
        orm_class = self.get_orm_class()
        q = self.get_query()
        v = list(orm_class.query.pks())
        self.assertEqual(0, len(v))
        count = 2
        self.insert(orm_class, count)

        v = list(orm_class.query.pks())
        self.assertEqual(2, len(v))

    def test___iter__(self):
        count = 5
        q = self.get_query()
        self.insert(q, count)

        rcount = 0
        for t in q:
            rcount += 1

        self.assertEqual(count, rcount)

    def test_has(self):
        q = self.get_query()
        self.assertFalse(q.has())

        count = 1
        self.insert(q, count)
        self.assertTrue(q.has())

    def test_all(self):
        count = 10
        q = self.get_query()
        self.insert(q, count)

        # if no limit is set then it should go through all results
        rcount = 0
        for r in q.copy().all():
            rcount += 1
        self.assertEqual(count, rcount)

        # if there is a limit then all should only go until that limit
        rcount = 0
        for r in q.copy().limit(1).all():
            rcount += 1
        self.assertEqual(1, rcount)

        # only go until the end of the results
        rcount = 0
        for r in q.copy().limit(6).offset(6).all():
            rcount += 1
        self.assertEqual(4, rcount)

    def test_in_field(self):
        q = self.get_query()
        q.in_foo([])
        self.assertFalse(q.can_get)

        q = self.get_query()
        q.in_foo([1, 2])
        self.assertEqual(q.fields_where[0].value, [1, 2,])

        q = self.get_query()
        q.in_foo([1])
        self.assertEqual(q.fields_where[0].value, [1])

        q = self.get_query()
        q.in_foo([1, 2])
        self.assertEqual(q.fields_where[0].value, [1, 2])

        q = self.get_query()
        q.in_foo(range(1, 3))
        self.assertEqual(q.fields_where[0].value, [1, 2,])

        q = self.get_query()
        q.in_foo((x for x in [1, 2]))
        self.assertEqual(q.fields_where[0].value, [1, 2,])

    def test_set(self):
        q = self.get_query()
        field_names = list(q.schema.fields.keys())
        fields = dict(zip(field_names, [None] * len(field_names)))
        q.set(**fields)
        self.assertEqual(fields, {f.name: f.value for f in q.fields_set})

        q = self.get_query()
        q.set(fields)
        self.assertEqual(fields, {f.name: f.value for f in q.fields_set})

    def test_select(self):
        q = self.get_query()
        fields_select = list(q.schema.fields.keys())
        q.select(*fields_select[0:-1])
        self.assertEqual(fields_select[0:-1], list(q.fields_select.names()))

        q = self.get_query()
        q.select(fields_select)
        self.assertEqual(fields_select, list(q.fields_select.names()))

        q = self.get_query()
        q.select(fields_select[0:-1], fields_select[-1])
        self.assertEqual(fields_select, list(q.fields_select.names()))

        # make sure chaining works
        q = self.get_query()
        q.select(fields_select[0]).select(*fields_select[1:])
        self.assertEqual(fields_select, list(q.fields_select.names()))

    def test_child_magic(self):

        orm_class = self.get_orm_class()
        class ChildQuery(Query):
            pass
        orm_class.query_class = ChildQuery

        q = orm_class.query
        q.is_foo(1) # if there is no error, it passed

        with self.assertRaises(AttributeError):
            q.aksdlfjldks_foo(2)

    def test_properties(self):
        q = self.get_query()
        r = q.schema
        self.assertTrue(r)

        r = q.interface
        self.assertEqual(r, q.orm_class.interface)
        self.assertTrue(r)

        q.orm_class = None
        self.assertFalse(q.schema)
        self.assertFalse(q.interface)

    def test___getattr__(self):
        q = self.get_query()
        q.is_foo(1)
        self.assertEqual(1, len(q.fields_where))
        pout.v(q.fields_where[0])
        self.assertEqual("eq", q.fields_where[0].operator)

        with self.assertRaises(AttributeError):
            q.testsfsdfsdft_fieldname(1, 2, 3)

    def test_append_operation(self):
        tests = [
            ("is_field", ["foo", 1], ["eq", "foo", 1]),
            ("not_field", ["foo", 1], ["ne", "foo", 1]),
            ("lte_field", ["foo", 1], ["lte", "foo", 1]),
            ("lt_field", ["foo", 1], ["lt", "foo", 1]),
            ("gte_field", ["foo", 1], ["gte", "foo", 1]),
            ("gt_field", ["foo", 1], ["gt", "foo", 1]),
            ("in_field", ["foo", (1, 2, 3)], ["in", "foo", [1, 2, 3]]),
            ("nin_field", ["foo", (1, 2, 3)], ["nin", "foo", [1, 2, 3]]),
        ]

        for i, t in enumerate(tests):
            q = self.get_query()
            cb = getattr(q, t[0])
            r = cb(*t[1])
            self.assertEqual(q, r)
            self.assertEqual(t[2][0], q.fields_where[0].operator)
            self.assertEqual(t[2][1], q.fields_where[0].name)
            self.assertEqual(t[2][2], q.fields_where[0].value)

        q = self.get_query()
        q.between_field("foo", 1, 2)
        self.assertEqual("gte", q.fields_where[0].operator)
        self.assertEqual("lte", q.fields_where[1].operator)

    def test_append_sort(self):
        tests = [
            ("append_sort", [1, "foo"], [1, "foo"]),
            ("append_sort", [-1, "foo"], [-1, "foo"]),
            ("append_sort", [5, "foo"], [1, "foo"]),
            ("append_sort", [-5, "foo"], [-1, "foo"]),
            ("asc_field", ["foo"], [1, "foo"]),
            ("desc_field", ["foo"], [-1, "foo"]),
        ]

        q = self.get_query()
        for i, t in enumerate(tests):
            cb = getattr(q, t[0])
            r = cb(*t[1])
            self.assertEqual(q, r)
            self.assertEqual(t[2][0], q.fields_sort[i].direction)
            self.assertEqual(t[2][1], q.fields_sort[i].name)

        with self.assertRaises(ValueError):
            q.append_sort(0, "foo")

    def test_bounds_methods(self):
        q = self.get_query()
        q.limit(10)
        self.assertEqual((10, 0), q.bounds.get())

        q.page(1)
        self.assertEqual((10, 0), q.bounds.get())

        q.offset(15)
        self.assertEqual((10, 15), q.bounds.get())

        q.page(2)
        self.assertEqual((10, 10), q.bounds.get())

        q.page(3)
        self.assertEqual((10, 20), q.bounds.get())

        q.page(0)
        self.assertEqual((10, 0), q.bounds.get())

        q.offset(0)
        self.assertEqual((10, 0), q.bounds.get())

        q.limit(0)
        self.assertEqual((0, 0), q.bounds.get())

    def test_insert_and_update(self):
        IUTorm = self.get_orm_class()
        q = IUTorm.query
        o = IUTorm(foo=1, bar="value 1")
        fields = o.depopulate(is_update=False)
        pk = q.copy().set(fields).insert()
        o = q.copy().get_pk(pk)
        self.assertLess(0, pk)
        self.assertTrue(o._created)
        self.assertTrue(o._updated)

        o = IUTorm(_id=o.pk, foo=2, bar="value 2", _created=fields["_created"])
        fields = o.depopulate(is_update=True)
        row_count = q.copy().set(fields).is_pk(pk).update()
        self.assertEqual(1, row_count)

        #time.sleep(0.1)
        o2 = q.copy().get_pk(pk)
        self.assertEqual(2, o2.foo)
        self.assertEqual("value 2", o2.bar)
        self.assertEqual(o._created, o2._created)
        self.assertNotEqual(o._updated, o2._updated)

    def test_update_bubble_up(self):
        """
        https://github.com/jaymon/prom/issues/11
        """
        orm = self.get_orm()
        orm.schema.set_field("che", prom.Field(str, False))
        orm.foo = 1
        orm.bar = "bar 1"
        orm.che = None
        orm.save()

        ret = orm.query.set_foo(2).set_bar("bar 2").not_che(None).update()
        self.assertEqual(0, ret)

        ret = orm.query.set_foo(2).set_bar("bar 2").is_che(None).update()
        self.assertEqual(1, ret)

    def test_delete(self):
        tclass = self.get_orm_class()
        first_pk = self.insert(tclass, 1)[0]

        with self.assertRaises(ValueError):
            r = tclass.query.delete()

        r = tclass.query.is_pk(first_pk).delete()
        self.assertEqual(1, r)

        r = tclass.query.is_pk(first_pk).delete()
        self.assertEqual(0, r)

    def test_get(self):
        TestGetTorm = self.get_orm_class()
        _ids = self.insert(TestGetTorm, 2)

        q = TestGetTorm.query
        for o in q.get():
            self.assertEqual(type(o), TestGetTorm)
            self.assertTrue(o._id in _ids)
            self.assertFalse(o.is_modified())

    def test_get_one(self):
        TestGetOneTorm = self.get_orm_class()
        _ids = self.insert(TestGetOneTorm, 2)

        q = TestGetOneTorm.query
        o = q.get_one()
        self.assertEqual(type(o), TestGetOneTorm)
        self.assertTrue(o._id in _ids)
        self.assertFalse(o.is_modified())

    def test_first_and_last(self):
        tclass = self.get_orm_class()
        first_pk = self.insert(tclass, 1)[0]

        t = tclass.query.first()
        self.assertEqual(first_pk, t.pk)

        t = tclass.query.last()
        self.assertEqual(first_pk, t.pk)

        last_pk = self.insert(tclass, 1)[0]
        t = tclass.query.first()
        self.assertEqual(first_pk, t.pk)

        t = tclass.query.last()
        self.assertEqual(last_pk, t.pk)

    def test_copy(self):
        q1 = self.get_query()
        q2 = q1.copy()

        q1.is_foo(1)
        self.assertEqual(1, len(q1.fields_where))
        self.assertEqual(0, len(q2.fields_where))

        self.assertNotEqual(id(q1), id(q2))
        self.assertNotEqual(id(q1.fields_where), id(q2.fields_where))
        self.assertNotEqual(id(q1.bounds), id(q2.bounds))


class IteratorTest(BaseTestCase):
    def test_cursor(self):
        count = 10
        orm_class = self.get_orm_class()
        self.insert(orm_class, count)

        q = orm_class.query
        it = q.cursor()
        self.assertEqual(10, len(it))
        with self.assertRaises(NotImplementedError):
            it[2]

    def test_all_wrapper(self):
        count = 100
        orm_class = self.get_orm_class()
        self.insert(orm_class, count)

        q = orm_class.query
        ait = AllIterator(q, chunk_limit=10)
        it = Iterator(ait)

        icount = 0
        for o in it:
            icount += 1
        self.assertEqual(count, icount)

        q = orm_class.query.limit(20)
        ait = AllIterator(q, chunk_limit=10)
        it = Iterator(ait)
        pks = []
        for o in it:
            pks.append(o.pk)
        self.assertEqual(20, len(pks))

        q = orm_class.query.limit(20).offset(10)
        ait = AllIterator(q, chunk_limit=10)
        it = Iterator(ait)
        pks2 = []
        for o in it:
            pks2.append(o.pk)
        self.assertEqual(20, len(pks))

        self.assertNotEqual(pks, pks2)

        q = orm_class.query.limit(20).offset(90)
        ait = AllIterator(q, chunk_limit=10)
        it = Iterator(ait)
        pks = []
        for o in it:
            pks.append(o.pk)
        self.assertEqual(10, len(pks))

    def get_iterator(self, count=5, limit=5, page=0):
        q = self.get_query()
        self.insert(q, count)
        i = q.get(limit, page)
        return i

    def test_custom(self):
        """make sure setting a custom Iterator class works normally and wrapped
        by an AllIterator()"""
        count = 3
        orm_class = self.get_orm_class()
        self.insert(orm_class, count)

        self.assertEqual(count, len(list(orm_class.query.get())))

        class CustomIterator(Iterator):
            def _filtered(self, o):
                return not o.pk == 1
        orm_class.iterator_class = CustomIterator


        self.assertEqual(count - 1, len(list(orm_class.query.get())))
        self.assertEqual(count - 1, len(list(orm_class.query.all())))

    def test_ifilter(self):
        count = 3
        _q = self.get_query()
        self.insert(_q, count)

        l = _q.copy().get()
        self.assertEqual(3, len(list(l)))

        l = _q.copy().get()
        def ifilter(o): return o.pk == 1
        l.ifilter = ifilter
        l2 = _q.copy().get()
        self.assertEqual(len(list(filter(ifilter, l2))), len(list(l)))

    def test_list_compatibility(self):
        count = 3
        _q = self.get_query()
        self.insert(_q, count)

        q = _q.copy()
        l = q.get()

        self.assertTrue(bool(l))
        self.assertEqual(count, l.count())
        self.assertEqual(list(range(1, count + 1)), list(l.pk))

        l.reverse()
        self.assertEqual(list(reversed(range(1, count + 1))), list(l.pk))

        r = l.pop(0)
        self.assertEqual(count, r.pk)

        r = l.pop()
        self.assertEqual(1, r.pk)

        pop_count = 0
        while l:
            pop_count += 1
            l.pop()
        self.assertGreater(pop_count, 0)

    def test_all_pop(self):
        """due to the nature of the all iterator, it makes no sense to support pop()"""
        with self.assertRaises(NotImplementedError):
            q = self.get_query().all().pop()

    def test_all_len(self):
        count = 10
        q = self.get_query()
        self.insert(q, count)
        g = q.select_foo().desc_bar().limit(5).offset(1).all()
        self.assertEqual(count, len(g))

    def test_all(self):
        count = 15
        q = self.get_query()
        self.insert(q, count)
        g = q.all()
        g.chunk_limit = 5

        self.assertEqual(1, g[0].pk)
        self.assertEqual(2, g[1].pk)
        self.assertEqual(3, g[2].pk)
        self.assertEqual(6, g[5].pk)
        self.assertEqual(13, g[12].pk)

        with self.assertRaises(IndexError):
            g[count + 5]

        for i, x in enumerate(g):
            if i > 7: break
        self.assertEqual(9, g[8].pk)

        gcount = 0
        for x in g: gcount += 1
        self.assertEqual(count, gcount)

        gcount = 0
        for x in g: gcount += 1
        self.assertEqual(count, gcount)

        self.assertEqual(count, len(g))

        g = q.all()
        self.assertEqual(count, len(g))

    def test_all_limit(self):
        count = 15
        q = self.get_query()
        self.insert(q, count)
        q.limit(5)
        g = q.all()

        self.assertEqual(3, g[2].pk)
        with self.assertRaises(IndexError):
            g[6]


    def test_values(self):
        count = 5
        _q = self.get_query()
        self.insert(_q, count)

        g = _q.copy().select_bar().get().values()
        icount = 0
        for v in g:
            self.assertTrue(isinstance(v, basestring))
            icount += 1
        self.assertEqual(count, icount)

        g = _q.copy().select_bar().select_foo().get().values()
        icount = 0
        for v in g:
            icount += 1
            self.assertTrue(isinstance(v[0], int))
            self.assertTrue(isinstance(v[1], basestring))
        self.assertEqual(count, icount)

        i = _q.copy().get()
        with self.assertRaises(ValueError):
            g = i.values()

    def test___iter__(self):
        count = 5
        i = self.get_iterator(count)

        rcount = 0
        for t in i:
            rcount += 1
        self.assertEqual(count, rcount)

        rcount = 0
        for t in i:
            self.assertTrue(isinstance(t, prom.Orm))
            rcount += 1
        self.assertEqual(count, rcount)

    def test___getitem__(self):
        count = 5
        i = self.get_iterator(count)
        for x in range(count):
            self.assertEqual(i[x].pk, i.results[x].pk)

        with self.assertRaises(IndexError):
            i[count + 1]

    def test___len__(self):
        count = 5
        i = self.get_iterator(count)
        self.assertEqual(len(i), count)

    def test___getattr__(self):
        count = 5
        i = self.get_iterator(count)
        rs = list(i.foo)
        self.assertEqual(count, len(rs))

        with self.assertRaises(AttributeError):
            i.kadfjkadfjkhjkgfkjfkjk_bogus_field

    def test_pk(self):
        count = 5
        i = self.get_iterator(count)
        rs = list(i.pk)
        self.assertEqual(count, len(rs))

    def test_has_more(self):
        limit = 3
        count = 5
        q = self.get_query()
        self.insert(q.orm_class, count)

        i = q.get(limit, 0)
        self.assertTrue(i.has_more)

        i = q.get(limit, 2)
        self.assertFalse(i.has_more)

        i = q.get(limit, 1)
        self.assertTrue(i.has_more)

        i = q.get(0, 0)
        self.assertFalse(i.has_more)


class CacheQueryTest(QueryTest):
    def setUp(self):
        CacheQuery.cached = {} # clear cache between tests
        super(CacheQueryTest, self).setUp()

    def get_orm_class(self, *args, **kwargs):
        orm_class = super(CacheQueryTest, self).get_orm_class(*args, **kwargs)
        orm_class.query_class = CacheQuery
        orm_class.query_class.cache_activate(True)
        return orm_class

    def test_cache_hit(self):
        orm_class = self.get_orm_class()
        self.insert(orm_class, 10)

        start = time.time()
        q = orm_class.query
        ref_pks = q.pks()
        stop = time.time()
        ref_duration = stop - start

        self.assertEqual(10, len(ref_pks))
        self.assertFalse(q.cache_hit)

        ref_pks = list(ref_pks)
        for x in range(10):
            start = time.time()
            q = orm_class.query
            pks = q.pks()
            stop = time.time()
            duration = stop - start
            #self.assertLess(duration, ref_duration)
            self.assertTrue(q.cache_hit)
            self.assertEqual(ref_pks, list(pks))

    def test_cache_contextmanager(self):
        orm_class = self.get_orm_class()
        orm_class.query_class.cache_activate(False)
        self.insert(orm_class, 10)

        with orm_class.query.cache(60):
            self.assertTrue(orm_class.query_class.cache_namespace.active)

        self.assertFalse(orm_class.query_class.cache_namespace.active)

    def test_cache_threading(self):

        orm_class = self.get_orm_class()
        orm_class.query_class.cache_activate(False)

        def one():
            with orm_class.query.cache():
                time.sleep(0.5)
                self.assertTrue(orm_class.query_class.cache_namespace.active)

        for x in range(500):
            self.assertFalse(orm_class.query_class.cache_namespace.active)

        t1 = Thread(target=one)
        t1.start()
        t1.join()

        self.assertFalse(orm_class.query_class.cache_namespace.active)

        #pout.v(orm_class.query.cache_namespace)
        #pout.v(orm_class.query.cache_namespace)


