# Optimizing queries with `EXPLAIN`
## 0) Previous experience with `EXPLAIN`
I remember inserting 1B+ todos only to get stuck in retrieving all of them. While exploring workarounds and trying to understand the failure I stumbled across `EXPLAIN ANALYSE`, only to quit it after a while, as even this step took ages to give me a result 🥹🥹 
## 1) Using `EXPLAIN` on the query to find the original url for a short code

![Using `EXPLAIN` on the query to find the original url for a short code](https://github.com/hs-4419/Query-Profiling/blob/main/Images/explain%20query%20to%20find%20the%20original%20url%20for%20a%20short%20code.png)
## 2) Using `EXPLAIN` on the query to fetch all rows created in the last 24 hours
![Using `EXPLAIN` on the query to fetch all rows created in the last 24 hours](https://github.com/hs-4419/Query-Profiling/blob/main/Images/explain%20query%20to%20fetch%20all%20rows%20created%20in%20the%20last%2024%20hours.png)
## 3) Using `EXPLAIN` on the query to fetch the latest 100 rows created
![Using `EXPLAIN` on the query to fetch the latest 100 rows created](https://github.com/hs-4419/Query-Profiling/blob/main/Images/explain%20query%20to%20fetch%20the%20latest%20100%20rows%20created.png)
## 4) Testing my understandig of `EXPLAIN` (Seq Scan vs Index)
| Query | Expeactation | Reality|
--|--|--
`EXPLAIN SELECT COUNT(*) FROM url_shortener` | Index | Seq Scan
`EXPLAIN SELECT COUNT(id) FROM url_shortener` | Index | Seq Scan
`EXPLAIN SELECT COUNT(short_url) FROM url_shortener` | Index | Seq Scan
`EXPLAIN SELECT COUNT(original_url) FROM url_shortener` | Seq Scan | Seq Scan
`EXPLAIN SELECT COUNT(created_at) FROM url_shortener` | Seq Scan | Seq Scan

- While executing count(*), count(id), count(short_code) I thought that postgress would use pk_index, pk_index and unique_index respectively, but the actual result for all the queries turned out to be Sequential Scan
- Have to understand this behaviour ...


## 5) Playing around with `EXPLAIN`
__Adding index on `created_at` column__
![Indexing created_on column](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B5%5D%20Indexing%20created_at%20column.png)
  
__Comparing `EXPLAIN` on [2](https://github.com/hs-4419/Query-Profiling/edit/main/README.md#2-using-explain-on-the-query-to-fetch-all-rows-created-in-the-last-24-hours) after adding index on created_at column__
`Filter by last 24 hours`
![Filter by last 24 hours](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B5%5D%20%5B2%5Dexplain%20query%20to%20fetch%20all%20rows%20created%20in%20the%20last%2024%20hours%20after%20adding%20index.png)

`Filter by last 14 hours`
![Filter by last 14 hours](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B5%5D%20%5B2%5Dexplain%20query%20to%20fetch%20all%20rows%20created%20in%20the%20last%2014%20hours%20after%20adding%20index.png)
__Comparing `EXPLAIN` on [3](https://github.com/hs-4419/Query-Profiling/edit/main/README.md#3-using-explain-on-the-query-to-fetch-the-latest-100-rows-created) after adding index on created_at column__
![Querying 3 after indexing](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B5%5D%20%5B3%5Dexplain%20query%20to%20fetch%20the%20latest%20100%20rows%20created%20after%20adding%20index.png)

`Executing query before indexing`
![Executing query before indexing](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Executing%20query%5B3%5D%20before%20indexing.png)
`Executing query after indexing`
![Executing query after indexing](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Executing%20query%5B3%5D%20after%20indexing.png)
> Indexing decreased the execution time by ~90%
> From 1385 ms to 141 ms

__Changes observed in [4](https://github.com/hs-4419/Query-Profiling/edit/main/README.md#4-testing-my-understandig-of-explain-seq-scan-vs-index) after adding index on created_at column__
![](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B4%5D%20explain%20query%20to%20count%20all.png)
![](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B4%5D%20explain%20query%20to%20count%20id.png)
![](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B4%5D%20explain%20query%20to%20count%20short_url.png)
![](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B4%5D%20explain%20query%20to%20count%20original_url.png)
![](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B4%5D%20explain%20query%20to%20count%20created_at.png)

| Query | Chnages|
--|--
`EXPLAIN SELECT COUNT(*) FROM url_shortener` | It's using the created_at column's index
`EXPLAIN SELECT COUNT(id) FROM url_shortener` | Seq Scan
`EXPLAIN SELECT COUNT(short_url) FROM url_shortener` | Seq Scan
`EXPLAIN SELECT COUNT(original_url) FROM url_shortener` | Seq Scan
`EXPLAIN SELECT COUNT(created_at) FROM url_shortener` |It's using the created_at column's index

__Drop the index__
![Drpping the index](https://github.com/hs-4419/Query-Profiling/blob/main/Images/%5B5%5D%20Dropping%20the%20index.png)
Everything fell back to the previous output  
All the queries in [4](https://github.com/hs-4419/Query-Profiling#4-testing-my-understandig-of-explain-seq-scan-vs-index) started using sequential scan
Not sure if something else was supposed to happen

  
__Observations__
- Indexing made the queries to run faster which were using those columns in where, filter clause
- Indexing alone can't fix the query optimization, the data present in the schema also affects the query planning
- For eg. in [2](https://github.com/hs-4419/Query-Profiling#2-using-explain-on-the-query-to-fetch-all-rows-created-in-the-last-24-hours) we are fetching all the rows created in last 24 hours, but since all the 10M records present in my schema are created within 1 day and I'm fetching all of them, so the query planner isn't using indexes rarther it's reading all the records sequentially. Whereas as soon as I change the condition to last 14 hours the query planner starts using indexes.
- Not sure about the behaviour for [4](https://github.com/hs-4419/Query-Profiling#4-testing-my-understandig-of-explain-seq-scan-vs-index) before and after adding index on created_on column. Even though pk_index and unique_col index are present why didn't it took into consideration??
- Shouldn't it use pk_index and unique_col index when using select count(id) and select count(short_url) just like it did in select count(created_at) ??

## 6) `EXPLAIN` vs `EXPLAIN ANALYSE`
Explain uses table and DB statistics to generate the time/cost of a query, whereas Explain Analyse actually runs the query and gives the realistic result (time, #rows, etc.)
## 7) Should we add index on every column?
Definitely NO 
- They should be added as per the need of the query and not everywhere
- If we add indexes in all the columns, then for each insert the no. of operations carried out will be (1 + #cols_to_be_indexed). Imagine a table having 4 cols, on every insert this table will perform 5 operations. Now imagine inserting 10M records, no. of operations will be 50 M, that's a lot of overhead not only based on operation but also on the size of the DB.
- Indexes have to be regularly checked and maintained, in postgress we use `VACCUM` to do the maintenance, even this process will be time consuming if anything and everything is indexed
- While querying with multiple conditions as here `select * from tb_name where cond1 and cond2 and cond3 ...` the query planner will use index only for first condition and thereafter it will put everything inder `FILTER`, defeating the whole purpose of indexing all the cols. For such cases we have to use composite index
- So, we should first find the data which is queried often and based on that we should take the decision on what to index and what not to index, and if in a col there is something which is more often queried , then instead of indexing complete query we should index only those rows with the specific value eg. `create index idx_selective_index_on_col table_name(col_name) where cond1 `
## 8) Demystifying output of `EXPLAIN`
- It's represented in a tree
- `cost=1000.00..249604.82 rows=1 width=39`
    - here `1000.00` is the __start up cost__ representing the computation cost before the query returned 1st row
    - `249604.82` is __total cost__ representing the total estimated cost of operation
    - `rows = 1` represents the #rows the query will return
    - `width = 39` depicts avg size of each row in bytes
    - here the unit of cost isn't secs, need to figure out what it's exactly ...
- __Scan Types__
    - __Seq Scan__ - scans/reads all the rows of the table (sequential scan)
    - __Index Scan__ - uses indexes to read only the rows required
- __Filters__ represent the condition applied after reading the data, eg. `where cond 1`, this cond 1 will be shown in filter node
- While using `EXPLAIN ANALYZE` will also come across actual time representing the time it took for the execution of query and here the unit is sec

## 9) Using `EXPLAIN` to understand the queries of [todo list](https://github.com/hs-4419/Todo-List?tab=readme-ov-file#todo-list)
1) Fetching todos of a user
   - Before creating index on user_id
     ![Fetching todos of a user before creating index on user_id](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B4%5D%20EXPLAIN%20Selecting%20todos%20of%20a%20user%20before%20indexing.png)
   - After creating index on user_id
     ![](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B4%5D%20EXPLAIN%20Selecting%20todos%20of%20a%20user%20after%20indexing.png)  
2) Updating a few todos
   ![Updating a few todos](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B5%5D%20EXPLAIN%20updating%20due_date.png)
3) Retrieving overdue todos
   ![Retrieving overdue todos](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B6%5D%20EXPLAIN%20Fetching%20overdue%20todos.png)
4) #todos per user
   ![ #todos per user](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B7%5D%20EXPLAIN%20%23todos%20each%20user%20has.png)
5) Updating description
   ![Updating description](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B8%5D%20EXPLAIN%20updating%20description.png)
6) Deleting a user
   ![Deleting a user](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B9%5D%20EXPLAIN%20deleting%20a%20user.png)
7) Get recent todo for each user with user details
   ![Get recent todo for each user with user details](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B10%5D%20EXPLAIN%20get%20latest%20todo%20for%20each%20user%20along%20with%20username.png)
8) #complete and #incomplete todos for each user with user details
   ![#complete and #incomplete todos for each user with user details](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B11%5D%20EXPLAIN%20get%20%23completed%20and%20%23notCompleted%20todos%20for%20each%20user%20with%20userDetails.png)
9) fetch all todos created within a week and are incomplete
    ![fetch all todos created within a week and are incomplete](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B14%5D%20EXPLAIN%20fetching%20all%20todos%20created%20within%20a%20week%20and%20are%20incomplete.png)
10) fetching users without any completion in one month
    ![fetching users without any completion in one month](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B16%5D%20EXPLAIN%20fetching%20users%20without%20any%20completion%20within%20a%20month.png)
11) using full text search
    - before creating inverted index on the ts_vector
      ![using full text search before creating inverted index on the ts_vector](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B19%5D%20EXPLAIN%20full%20text%20search%20before%20creating%20GIN.png)
    - after creating inverted index on the ts_vector
      ![using full text search after creating inverted index on the ts_vector](https://github.com/hs-4419/Query-Profiling/blob/main/Images/Bonus/%5B19%5D%20EXPLAIN%20full%20text%20search%20after%20creating%20GIN.png)
