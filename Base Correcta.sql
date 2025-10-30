/*
    SQL Server script to create the database schema for the Six Sigma PVC dashboard.

    This script extends the original design to model additional entities
    identified during the engineering of requirements.  It creates both
    catalogue tables (roles, users, lines, products, defect types, control
    parameters) and transactional tables (measurements, process indicators,
    observations, defects and scrap).  Sample data are inserted to enable
    immediate testing of the application.  Run this script in SQL Server
    Management Studio or using the sqlcmd utility.

    To execute via sqlcmd:

        sqlcmd -S localhost -U sa -P <password> -i create_db_sqlserver_complete.sql

*/

/* Create database if it does not exist */
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'sixsigma2')
BEGIN
    CREATE DATABASE sixsigma;
END
GO

USE sixsigma;
GO

/* ----------------------------------------------------------------------- */
/* 1. Catalogue tables                                                     */
/* ----------------------------------------------------------------------- */

-- Roles: defines the different permission levels within the application
IF OBJECT_ID('dbo.roles', 'U') IS NOT NULL
    DROP TABLE dbo.roles;
CREATE TABLE dbo.roles (
    id_rol         INT IDENTITY(1,1) PRIMARY KEY,
    nombre         NVARCHAR(50) NOT NULL,
    descripcion    NVARCHAR(255)
);

-- Users: stores system users and associates them with a role.
-- Note: passwords should be stored as secure hashes; here we use plain text
-- for demonstration purposes only.
IF OBJECT_ID('dbo.usuarios', 'U') IS NOT NULL
    DROP TABLE dbo.usuarios;
CREATE TABLE dbo.usuarios (
    id_usuario      INT IDENTITY(1,1) PRIMARY KEY,
    nombre          NVARCHAR(50) NOT NULL,
    apellido        NVARCHAR(50) NOT NULL,
    email           NVARCHAR(100) NOT NULL UNIQUE,
    contrasena_hash NVARCHAR(255) NOT NULL,
    id_rol          INT NOT NULL FOREIGN KEY REFERENCES dbo.roles(id_rol),
    fecha_creacion  DATETIME NOT NULL DEFAULT GETDATE()
);

-- Production lines
IF OBJECT_ID('dbo.linea_produccion', 'U') IS NOT NULL
    DROP TABLE dbo.linea_produccion;
CREATE TABLE dbo.linea_produccion (
    id_linea    INT IDENTITY(1,1) PRIMARY KEY,
    nombre      NVARCHAR(50) NOT NULL,
    descripcion NVARCHAR(255)
);

-- Products manufactured on the lines
IF OBJECT_ID('dbo.producto', 'U') IS NOT NULL
    DROP TABLE dbo.producto;
CREATE TABLE dbo.producto (
    id_producto INT IDENTITY(1,1) PRIMARY KEY,
    nombre      NVARCHAR(100) NOT NULL,
    dimension   NVARCHAR(50),
    sdr         NVARCHAR(20),
    descripcion NVARCHAR(255)
);

-- Types of defects (e.g., dimensional, material, cosmetic, structural)
IF OBJECT_ID('dbo.defecto_tipo', 'U') IS NOT NULL
    DROP TABLE dbo.defecto_tipo;
CREATE TABLE dbo.defecto_tipo (
    id_defecto_tipo INT IDENTITY(1,1) PRIMARY KEY,
    nombre          NVARCHAR(100) NOT NULL,
    descripcion     NVARCHAR(255)
);

-- Control parameters: target and tolerance for each critical variable of a product
IF OBJECT_ID('dbo.parametro_control', 'U') IS NOT NULL
    DROP TABLE dbo.parametro_control;
CREATE TABLE dbo.parametro_control (
    id_parametro    INT IDENTITY(1,1) PRIMARY KEY,
    id_producto     INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id_producto),
    id_linea        INT NOT NULL FOREIGN KEY REFERENCES dbo.linea_produccion(id_linea),
    nombre          NVARCHAR(100) NOT NULL,
    valor_objetivo  FLOAT NOT NULL,
    limite_superior FLOAT NOT NULL,
    limite_inferior FLOAT NOT NULL
);

/* ----------------------------------------------------------------------- */
/* 2. Transactional tables                                                */
/* ----------------------------------------------------------------------- */

-- Measurements: raw measurements captured from the PLC / Excel logs
IF OBJECT_ID('dbo.medicion', 'U') IS NOT NULL
    DROP TABLE dbo.medicion;
CREATE TABLE dbo.medicion (
    id_medicion INT IDENTITY(1,1) PRIMARY KEY,
    fecha       DATE NOT NULL,
    id_linea    INT NOT NULL FOREIGN KEY REFERENCES dbo.linea_produccion(id_linea),
    id_producto INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id_producto),
    orden       NVARCHAR(50),
    codigo      NVARCHAR(50),
    t1          FLOAT,
    t2          FLOAT,
    t3          FLOAT,
    t4          FLOAT,
    promedio    FLOAT,
    th          FLOAT
);

-- Process indicators: statistical metrics calculated from groups of measurements
IF OBJECT_ID('dbo.indicador_proceso', 'U') IS NOT NULL
    DROP TABLE dbo.indicador_proceso;
CREATE TABLE dbo.indicador_proceso (
    id_indicador  INT IDENTITY(1,1) PRIMARY KEY,
    fecha         DATE NOT NULL,
    id_linea      INT NOT NULL FOREIGN KEY REFERENCES dbo.linea_produccion(id_linea),
    id_producto   INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id_producto),
    cp            FLOAT,
    cpk           FLOAT,
    sigma         FLOAT,
    comentarios   NVARCHAR(255)
);

-- Observations: notes and corrective actions linked to a measurement
IF OBJECT_ID('dbo.observacion', 'U') IS NOT NULL
    DROP TABLE dbo.observacion;
CREATE TABLE dbo.observacion (
    id_observacion    INT IDENTITY(1,1) PRIMARY KEY,
    fecha             DATE NOT NULL,
    id_medicion       INT NOT NULL FOREIGN KEY REFERENCES dbo.medicion(id_medicion),
    descripcion       NVARCHAR(255) NOT NULL,
    accion_correctiva NVARCHAR(255)
);

-- Defects: records the number of defects per type in a given batch or period
IF OBJECT_ID('dbo.defecto', 'U') IS NOT NULL
    DROP TABLE dbo.defecto;
CREATE TABLE dbo.defecto (
    id_defecto       INT IDENTITY(1,1) PRIMARY KEY,
    fecha            DATE NOT NULL,
    id_linea         INT NOT NULL FOREIGN KEY REFERENCES dbo.linea_produccion(id_linea),
    id_producto      INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id_producto),
    id_defecto_tipo  INT NOT NULL FOREIGN KEY REFERENCES dbo.defecto_tipo(id_defecto_tipo),
    cantidad         INT NOT NULL,
    lote             NVARCHAR(50),
    turno            NVARCHAR(50)
);

-- Scrap: summary of defective quantity vs total produced per day/shift
IF OBJECT_ID('dbo.scrap', 'U') IS NOT NULL
    DROP TABLE dbo.scrap;
CREATE TABLE dbo.scrap (
    id_scrap          INT IDENTITY(1,1) PRIMARY KEY,
    fecha             DATE NOT NULL,
    id_linea          INT NOT NULL FOREIGN KEY REFERENCES dbo.linea_produccion(id_linea),
    id_producto       INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id_producto),
    total_producido   INT NOT NULL,
    total_defectuoso  INT NOT NULL,
    porcentaje_scrap  AS (CASE WHEN total_producido = 0 THEN 0 ELSE CAST(total_defectuoso AS FLOAT) / total_producido * 100 END)
);

/* ----------------------------------------------------------------------- */
/* 3. Sample data                                                         */
/* ----------------------------------------------------------------------- */

-- Insert roles
INSERT INTO dbo.roles (nombre, descripcion) VALUES
('Administrador', 'Acceso completo al sistema'),
('Ingeniero de calidad', 'Puede visualizar y cargar datos de producción'),
('Supervisor', 'Visualiza estadísticas y registra mediciones'),
('Operador', 'Carga archivos de producción');

-- Insert a default user for testing (passwords must be hashed in production)
INSERT INTO dbo.usuarios (nombre, apellido, email, contrasena_hash, id_rol)
VALUES ('Usuario', 'Admin', 'admin@example.com', 'admin', 1);

-- Insert lines of production
INSERT INTO dbo.linea_produccion (nombre, descripcion) VALUES
('Línea 3', 'Extrusora de tubos P.V.C. ½″ SDR 315 PSI'),
('Línea 4', 'Extrusora de tubos P.V.C. 1″');

-- Insert products
INSERT INTO dbo.producto (nombre, dimension, sdr, descripcion) VALUES
('Tubo P.V.C. ½″', '½"', '315', 'Tubo de presión SDR 315 PSI'),
('Tubo P.V.C. 1″', '1"', '315', 'Tubo de presión SDR 315 PSI');

-- Insert defect types
INSERT INTO dbo.defecto_tipo (nombre, descripcion) VALUES
('Dimensional', 'Fuera de tolerancia en diámetro o espesor'),
('Material', 'Impurezas, burbujas o fisuras'),
('Cosmético', 'Rayas, manchas o deformaciones superficiales');

-- Insert sample measurements (10 records) for the half‑inch product
INSERT INTO dbo.medicion (
    fecha, id_linea, id_producto, orden, codigo, t1, t2, t3, t4, promedio, th
) VALUES
('2025-07-01', 1, 1, 'ORD001', 'P001', 64.0, 66.5, 63.0, 65.0, 64.625, 55.0),
('2025-07-01', 1, 1, 'ORD002', 'P001', 62.0, 60.5, 59.0, 61.0, 60.625, 58.0),
('2025-07-02', 1, 1, 'ORD003', 'P001', 70.0, 68.5, 69.0, 71.0, 69.625, 53.0),
('2025-07-03', 1, 1, 'ORD004', 'P001', 58.0, 57.5, 56.0, 59.0, 57.625, 60.0),
('2025-07-04', 1, 1, 'ORD005', 'P001', 65.0, 64.5, 66.0, 64.0, 64.875, 56.0),
('2025-07-05', 1, 1, 'ORD006', 'P001', 61.0, 62.0, 60.0, 62.5, 61.375, 57.0),
('2025-07-06', 1, 1, 'ORD007', 'P001', 67.0, 69.5, 68.0, 66.0, 67.625, 54.0),
('2025-07-07', 1, 1, 'ORD008', 'P001', 63.0, 62.5, 64.0, 63.0, 63.125, 58.0),
('2025-07-08', 1, 1, 'ORD009', 'P001', 59.0, 60.5, 61.0, 60.0, 60.125, 59.0),
('2025-07-09', 1, 1, 'ORD010', 'P001', 68.0, 67.5, 66.0, 68.0, 67.375, 55.0);

-- Insert sample control parameters for the half‑inch product on line 3
INSERT INTO dbo.parametro_control (
    id_producto, id_linea, nombre, valor_objetivo, limite_superior, limite_inferior
) VALUES
    (1, 1, 'Ciclo promedio (s)', 60.0, 90.0, 30.0),
    (1, 1, 'Tubos por hora',    60.0, 80.0, 40.0);

-- Insert sample process indicators for the half‑inch product
INSERT INTO dbo.indicador_proceso (
    fecha, id_linea, id_producto, cp, cpk, sigma, comentarios
) VALUES
('2025-07-10', 1, 1, 1.45, 1.33, 4.5, 'Estable con ligera variación'),
('2025-07-11', 1, 1, 1.30, 1.20, 4.2, 'Variabilidad moderada');

-- Insert sample observations
INSERT INTO dbo.observacion (
    fecha, id_medicion, descripcion, accion_correctiva
) VALUES
('2025-07-03', 3, 'Promedio por encima del objetivo', 'Ajuste de velocidad de tornillo'),
('2025-07-05', 5, 'Variación excesiva en el tiempo de ciclo', 'Revisión de la temperatura del extrusor');

-- Insert sample defect counts
INSERT INTO dbo.defecto (
    fecha, id_linea, id_producto, id_defecto_tipo, cantidad, lote, turno
) VALUES
('2025-07-01', 1, 1, 1, 5, 'Lote001', 'Mañana'),
('2025-07-02', 1, 1, 2, 3, 'Lote002', 'Tarde'),
('2025-07-03', 1, 1, 1, 2, 'Lote003', 'Noche');

-- Insert sample scrap summary
INSERT INTO dbo.scrap (
    fecha, id_linea, id_producto, total_producido, total_defectuoso
) VALUES
('2025-07-01', 1, 1, 1000, 15),
('2025-07-02', 1, 1, 950, 10),
('2025-07-03', 1, 1, 900, 8);

/* End of script */