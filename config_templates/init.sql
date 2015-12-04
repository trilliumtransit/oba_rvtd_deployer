CREATE USER {pg_username} PASSWORD '{pg_password}';
CREATE ROLE {pg_role};
GRANT {pg_role} TO {pg_username};
CREATE DATABASE org_onebusaway_users ENCODING = 'UTF8'; 
CREATE DATABASE org_onebusaway_database ENCODING = 'UTF8';
GRANT ALL ON DATABASE org_onebusaway_users TO {pg_role};
GRANT ALL ON DATABASE org_onebusaway_database TO {pg_role};