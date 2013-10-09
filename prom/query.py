"""
Classes and stuff that handle querying the interface for a passed in Orm class
"""
#    query.table("table_name").is_foo(1).desc_bar().limit(10).page(2).get()
#    query.table("table_name").is_foo(1).desc_bar().set_limit(10).set_page(2).get()
#    query.table("table_name").is_foo(1).desc_bar().with_limit(10).with_page(2).get()
#    query.table("table_name").is_foo(1).desc_bar().use_limit(10).use_page(2).get()
#    query.table("table_name").is_foo(1).desc_bar().limit_to(10).on_page(2).with_offset(5).get()


class Iterator(object):
    """
    smartly iterate through a result set

    this is returned from the Query.get() and Query.all() methods, it acts as much
    like a list as possible to make using it as seemless as can be

    fields --
        has_more -- boolean -- True if there are more results in the db, false otherwise

    examples --
        # iterate through all the primary keys of some orm
        for pk in SomeOrm.query.all().pk:
            print pk
    """
    def __init__(self, results, orm=None, has_more=False):
        self.results = results
        self.orm = orm
        self.has_more = has_more
        self.iresults = self.results.__iter__() # hack

    def next(self):
        r = self._get_result(self.iresults.next())
        return r

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.results)

    def __getitem__(self, k):
        k = int(k)
        return self._get_result(self.results[k])

    def __getattr__(self, k):
        """
        this allows you to focus in on certain fields of results

        It's just an easier way of doing: (getattr(x, k, None) for x in self)
        """
        if k == 'pk': k = self.orm.schema.pk
        if k not in self.orm.schema.fields:
            raise KeyError("key {} is not in the {} schema".format(k, self.orm.schema))

        return (getattr(r, k, None) for r in self)

    def _get_result(self, d):
        r = None
        if self.orm:
            r = self.orm.populate(d)
        else:
            r = d

        return r


class AllIterator(Iterator):
    """
    Similar to Iterator, but will chunk up results and make another query for the next
    chunk of results until there are no more results of the passed in Query(), so you
    can just iterate through every row of the db without worrying about pulling too
    many rows at one time
    """
    def __init__(self, query):
        limit, offset, _ = query.get_bounds()
        if not limit:
            limit = 5000

        self.chunk_limit = limit
        self.offset = offset
        self.query = query
        super(AllIterator, self).__init__(results=[], orm=self.query.orm)

    def __iter__(self):
        has_more = True
        while has_more:
            self.results = self.query.set_offset(self.offset).get(self.chunk_limit)
            has_more = self.results.has_more
            for r in self.results:
                yield r

            self.offset += self.chunk_limit


class Query(object):
    """
    Handle standard query creation and allow interface querying

    example --
        q = Query(orm)
        q.is_foo(1).desc_bar().set_limit(10).set_page(2).get()
    """
    def __init__(self, orm=None, *args, **kwargs):

        # needed to use the db querying methods like get(), if you just want to build
        # a query then you don't need to bother passing this in
        self.orm = orm

        self.fields = {}
        self.fields_where = []
        self.fields_sort = []
        self.bounds = {}
        self.args = args
        self.kwargs = kwargs

    def __iter__(self):
        return self.get()

    def set_field(self, field_name, field_val=None):
        """
        set a field into .fields attribute

        this has a dual role, in select queries, these are the select fields, but in insert/update
        queries, these are the fields that will be inserted/updated into the db
        """
        #self.fields.append([field_name, field_val])
        self.fields[field_name] = field_val
        return self

    def set_fields(self, fields=None, **fields_kwargs):
        """
        completely replaces the current .fields with fields and fields_kwargs combined
        """
        if not fields: fields = {}
        fields.update(fields_kwargs)
        self.fields = fields
        return self

    def is_field(self, field_name, field_val):
        self.fields_where.append(["is", field_name, field_val])
        return self

    def not_field(self, field_name, field_val):
        self.fields_where.append(["not", field_name, field_val])
        return self

    def between_field(self, field_name, low, high):
        self.lte_field(field_name, low)
        self.gte_field(field_name, high)
        return self

    def lte_field(self, field_name, field_val):
        self.fields_where.append(["lte", field_name, field_val])
        return self

    def lt_field(self, field_name, field_val):
        self.fields_where.append(["lt", field_name, field_val])
        return self

    def gte_field(self, field_name, field_val):
        self.fields_where.append(["gte", field_name, field_val])
        return self

    def gt_field(self, field_name, field_val):
        self.fields_where.append(["gt", field_name, field_val])
        return self

    def in_field(self, field_name, field_vals):
        """
        field_vals -- list -- a list of field_val values
        """
        self.fields_where.append(["in", field_name, list(field_vals)])
        return self

    def nin_field(self, field_name, field_vals):
        """
        field_vals -- list -- a list of field_val values
        """
        self.fields_where.append(["nin", field_name, list(field_vals)])
        return self

    def sort_field(self, field_name, direction):
        if direction > 0:
            direction = 1
        elif direction < 0:
            direction = -1
        else:
            raise ValueError("direction {} is undefined".format(direction))

        self.fields_sort.append([direction, field_name])
        return self

    def asc_field(self, field_name):
        self.sort_field(field_name, 1)
        return self

    def desc_field(self, field_name):
        self.sort_field(field_name, -1)
        return self

    def __getattr__(self, method_name):

        command, field_name = self._split_method(method_name)

        def callback(*args, **kwargs):
            field_method_name = "{}_field".format(command)
            command_field_method = None

            if getattr(type(self), field_method_name, None):
                command_field_method = getattr(self, field_method_name)
            else:
                raise AttributeError('No "{}" method derived from "{}"'.format(field_method_name, method_name))

            return command_field_method(field_name, *args, **kwargs)

        return callback

    def _split_method(self, method_name):
        command, field_name = method_name.split(u"_", 1)
        return command, field_name

    def set_limit(self, limit):
        self.bounds['limit'] = int(limit)
        return self

    def set_offset(self, offset):
        self.bounds.pop("page", None)
        self.bounds['offset'] = int(offset)
        return self

    def set_page(self, page):
        self.bounds.pop("offset", None)
        self.bounds['page'] = int(page)
        return self

    def get_bounds(self):

        limit = offset = page = limit_paginate = 0
        if "limit" in self.bounds and self.bounds["limit"] > 0:
            limit = self.bounds["limit"]
            limit_paginate = limit + 1

        if "offset" in self.bounds:
            offset = self.bounds["offset"]
            offset = offset if offset >= 0 else 0

        else:
            if "page" in self.bounds:
                page = self.bounds["page"]
                page = page if page >= 1 else 1
                offset = (page - 1) * limit

        return (limit, offset, limit_paginate)

    def has_bounds(self):
        return len(self.bounds) > 0

    def get(self, limit=None, page=None):
        """
        get results from the db

        return -- Iterator()
        """
        if limit is not None:
            self.set_limit(limit)
        if page is not None:
            self.set_page(page)

        has_more = False
        limit, offset, limit_paginate = self.get_bounds()
        if limit_paginate:
            self.set_limit(limit_paginate)

        results = self._query('get')

        if limit_paginate:
            self.set_limit(limit)
            if len(results) == limit_paginate:
                has_more = True
                results.pop(limit)

        return Iterator(results, orm=self.orm, has_more=has_more)

    def all(self):
        """
        return every possible result for this query

        This is smart about returning results and will use the set limit (or a default if no
        limit was set) to chunk up the results, this means you can work your way through
        really big result sets without running out of memory

        return -- Iterator()
        """
        return AllIterator(self)

    def get_one(self):
        """get one row from the db"""
        o = None
        d = self._query('get_one')
        if d:
            o = self.orm.populate(d)
        return o

    def get_pk(self, field_val):
        """convenience method for running is__id(_id).get_one() since this is so common"""
        field_name = self.orm.schema.pk
        return self.is_field(field_name, field_val).get_one()

    def count(self):
        """return the count of the criteria"""
        return self._query('count')

    def set(self):
        """persist the .fields using .fields_where (if available)"""
        return self._query('set')

    def delete(self):
        """remove fields matching the where criteria"""
        return self._query('delete')

    def get_query(self, query_str, *query_args, **query_options):
        """
        use the interface query method to pass in your own raw query
        """
        i = self.orm.interface
        return i.query(query_str, *query_args, **query_options)

    def _query(self, method_name):
        i = self.orm.interface
        s = self.orm.schema
        return getattr(i, method_name)(s, self)

    def _create_orm(self, d):
        o = self.orm(**d)
        o.reset_modified()
        return o

