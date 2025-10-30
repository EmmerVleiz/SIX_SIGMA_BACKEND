IF DB_ID('sixsigma') IS NULL
BEGIN
    CREATE DATABASE sixsigma;
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = 'sixsigma_user')
BEGIN
    CREATE LOGIN sixsigma_user WITH PASSWORD = 'StrongPass!23';
END
GO

USE sixsigma;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'sixsigma_user')
BEGIN
    CREATE USER sixsigma_user FOR LOGIN sixsigma_user;
    EXEC sp_addrolemember 'db_datareader', 'sixsigma_user';
    EXEC sp_addrolemember 'db_datawriter', 'sixsigma_user';
END
GO
