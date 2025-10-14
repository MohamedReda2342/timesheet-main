mysql> use timesheet_app
Database changed
mysql> show tables
    -> ;
+-------------------------+
| Tables_in_timesheet_app |
+-------------------------+
| project_approvers       |
| projects                |
| timesheet_entries       |
| timesheets              |
| users                   |
+-------------------------+
5 rows in set (0.090 sec)

mysql> describe users;
+---------------+---------------------------------+------+-----+---------+----------------+
| Field         | Type                            | Null | Key | Default | Extra          |
+---------------+---------------------------------+------+-----+---------+----------------+
| user_id       | int                             | NO   | PRI | NULL    | auto_increment |
| first_name    | varchar(100)                    | YES  |     | NULL    |                |
| last_name     | varchar(100)                    | YES  |     | NULL    |                |
| email         | varchar(255)                    | YES  | UNI | NULL    |                |
| password_hash | varchar(255)                    | NO   |     | NULL    |                |
| organization  | varchar(255)                    | YES  |     | NULL    |                |
| role          | enum('user','approver','admin') | NO   |     | NULL    |                |
+---------------+---------------------------------+------+-----+---------+----------------+
7 rows in set (0.064 sec)

mysql> describe timesheets;
+--------------+-------------------------------------------------+------+-----+---------+----------------+
| Field        | Type                                            | Null | Key | Default | Extra          |
+--------------+-------------------------------------------------+------+-----+---------+----------------+
| timesheet_id | int                                             | NO   | PRI | NULL    | auto_increment |
| user_id      | int                                             | NO   | MUL | NULL    |                |
| week_start   | date                                            | NO   |     | NULL    |                |
| hours_worked | int                                             | NO   |     | 0       |                |
| project      | varchar(255)                                    | YES  |     | NULL    |                |
| status       | enum('draft','submitted','approved','rejected') | YES  |     | draft   |                |
| approver_id  | int                                             | YES  | MUL | NULL    |                |
| submitted_at | timestamp                                       | YES  |     | NULL    |                |
| approved_at  | timestamp                                       | YES  |     | NULL    |                |
+--------------+-------------------------------------------------+------+-----+---------+----------------+
9 rows in set (0.029 sec)

mysql> describe timesheet_entries
    -> ;
+--------------+--------------+------+-----+---------+----------------+
| Field        | Type         | Null | Key | Default | Extra          |
+--------------+--------------+------+-----+---------+----------------+
| entry_id     | int          | NO   | PRI | NULL    | auto_increment |
| timesheet_id | int          | NO   | MUL | NULL    |                |
| entry_date   | date         | NO   |     | NULL    |                |
| hours_worked | decimal(5,2) | NO   |     | NULL    |                |
| activity     | varchar(255) | YES  |     | NULL    |                |
| project      | varchar(255) | YES  |     | NULL    |                |
| project_id   | int          | YES  | MUL | NULL    |                |
+--------------+--------------+------+-----+---------+----------------+
7 rows in set (0.030 sec)


mysql> describe projects;
+--------------+--------------------------------------+------+-----+---------+----------------+
| Field        | Type                                 | Null | Key | Default | Extra          |
+--------------+--------------------------------------+------+-----+---------+----------------+
| project_id   | int                                  | NO   | PRI | NULL    | auto_increment |
| project_name | varchar(255)                         | NO   |     | NULL    |                |
| client_name  | varchar(255)                         | YES  |     | NULL    |                |
| start_date   | date                                 | YES  |     | NULL    |                |
| end_date     | date                                 | YES  |     | NULL    |                |
| status       | enum('active','on-hold','completed') | YES  |     | active  |                |
+--------------+--------------------------------------+------+-----+---------+----------------+
6 rows in set (0.027 sec)

mysql> describe project_approvers
    -> ;
+------------+------+------+-----+---------+-------+
| Field      | Type | Null | Key | Default | Extra |
+------------+------+------+-----+---------+-------+
| project_id | int  | NO   | PRI | NULL    |       |
| user_id    | int  | NO   | PRI | NULL    |       |
+------------+------+------+-----+---------+-------+
2 rows in set (0.020 sec)

