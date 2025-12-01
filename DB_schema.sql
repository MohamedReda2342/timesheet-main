USE [att_db]
GO

/****** Object:  Table [dbo].[approvals]    Script Date: 12/1/2025 12:26:22 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[approvals](
	[approval_id] [int] IDENTITY(1,1) NOT NULL,
	[entry_id] [int] NOT NULL,
	[approver_id] [int] NOT NULL,
	[decision] [nvarchar](max) NOT NULL,
	[comment] [nvarchar](max) NULL,
	[decision_ts] [datetime] NOT NULL,
 CONSTRAINT [PK_dbo.approvals] PRIMARY KEY CLUSTERED 
(
	[approval_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[approvals]  WITH CHECK ADD  CONSTRAINT [FK_approvals_Employee_approver_id] FOREIGN KEY([approver_id])
REFERENCES [dbo].[Employee] ([EmpId])
GO

ALTER TABLE [dbo].[approvals] CHECK CONSTRAINT [FK_approvals_Employee_approver_id]
GO

ALTER TABLE [dbo].[approvals]  WITH CHECK ADD  CONSTRAINT [FK_dbo.approvals_dbo.timesheet_entries_entry_id] FOREIGN KEY([entry_id])
REFERENCES [dbo].[timesheet_entries] ([entry_id])
ON DELETE CASCADE
GO

ALTER TABLE [dbo].[approvals] CHECK CONSTRAINT [FK_dbo.approvals_dbo.timesheet_entries_entry_id]
GO


USE [att_db]
GO

/****** Object:  Table [dbo].[Assignments]    Script Date: 12/1/2025 12:26:52 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Assignments](
	[AssignmentId] [int] IDENTITY(1,1) NOT NULL,
	[task_id] [int] NOT NULL,
	[EmpId] [int] NOT NULL,
	[assignment_name] [nvarchar](255) NULL,
	[planned_hours] [int] NOT NULL,
	[notes] [nvarchar](max) NULL,
	[start_date] [datetime] NULL,
	[end_date] [datetime] NULL,
	[status] [nvarchar](50) NULL,
	[created_at] [datetime] NULL,
PRIMARY KEY CLUSTERED 
(
	[AssignmentId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[Assignments] ADD  DEFAULT ('active') FOR [status]
GO

ALTER TABLE [dbo].[Assignments] ADD  DEFAULT (getdate()) FOR [created_at]
GO

ALTER TABLE [dbo].[Assignments]  WITH CHECK ADD  CONSTRAINT [FK_Assignments_Employee] FOREIGN KEY([EmpId])
REFERENCES [dbo].[Employee] ([EmpId])
GO

ALTER TABLE [dbo].[Assignments] CHECK CONSTRAINT [FK_Assignments_Employee]
GO

ALTER TABLE [dbo].[Assignments]  WITH CHECK ADD  CONSTRAINT [FK_Assignments_Tasks] FOREIGN KEY([task_id])
REFERENCES [dbo].[tasks] ([task_id])
ON DELETE CASCADE
GO

ALTER TABLE [dbo].[Assignments] CHECK CONSTRAINT [FK_Assignments_Tasks]
GO

USE [att_db]
GO

/****** Object:  Table [dbo].[Department]    Script Date: 12/1/2025 12:27:12 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Department](
	[DepId] [int] IDENTITY(1,1) NOT NULL,
	[DepName] [nvarchar](50) NOT NULL,
 CONSTRAINT [PK_Department] PRIMARY KEY CLUSTERED 
(
	[DepId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO


USE [att_db]
GO

/****** Object:  Table [dbo].[Employee]    Script Date: 12/1/2025 12:27:36 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Employee](
	[EmpId] [int] IDENTITY(1,1) NOT NULL,
	[EmpName] [nvarchar](max) NOT NULL,
	[DepId] [int] NULL,
	[EmpPositionId] [int] NULL,
	[EmpEmail] [nvarchar](max) NOT NULL,
	[Password] [nvarchar](max) NOT NULL,
	[ParentManager] [int] NULL,
	[ApprovalTypeId] [int] NOT NULL,
	[SAP_ID] [int] NOT NULL,
	[UserTypeId] [int] NULL,
	[IsFirstLogin] [bit] NOT NULL,
	[EmailCC] [bit] NULL,
 CONSTRAINT [PK_Employee_1] PRIMARY KEY CLUSTERED 
(
	[EmpId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[Employee]  WITH CHECK ADD  CONSTRAINT [FK_Employee_ApprovalType] FOREIGN KEY([ApprovalTypeId])
REFERENCES [dbo].[ApprovalType] ([ApprovalTypeId])
GO

ALTER TABLE [dbo].[Employee] CHECK CONSTRAINT [FK_Employee_ApprovalType]
GO

ALTER TABLE [dbo].[Employee]  WITH CHECK ADD  CONSTRAINT [FK_Employee_Department] FOREIGN KEY([DepId])
REFERENCES [dbo].[Department] ([DepId])
GO

ALTER TABLE [dbo].[Employee] CHECK CONSTRAINT [FK_Employee_Department]
GO

ALTER TABLE [dbo].[Employee]  WITH CHECK ADD  CONSTRAINT [FK_Employee_Employee1] FOREIGN KEY([ParentManager])
REFERENCES [dbo].[Employee] ([EmpId])
GO

ALTER TABLE [dbo].[Employee] CHECK CONSTRAINT [FK_Employee_Employee1]
GO

ALTER TABLE [dbo].[Employee]  WITH CHECK ADD  CONSTRAINT [FK_Employee_EmployeePosition] FOREIGN KEY([EmpPositionId])
REFERENCES [dbo].[EmployeePosition] ([EmpPositionId])
GO

ALTER TABLE [dbo].[Employee] CHECK CONSTRAINT [FK_Employee_EmployeePosition]
GO

ALTER TABLE [dbo].[Employee]  WITH CHECK ADD  CONSTRAINT [FK_Employee_UserType] FOREIGN KEY([UserTypeId])
REFERENCES [dbo].[UserType] ([UserTypeId])
GO

ALTER TABLE [dbo].[Employee] CHECK CONSTRAINT [FK_Employee_UserType]
GO


USE [att_db]
GO

/****** Object:  Table [dbo].[project_approvers]    Script Date: 12/1/2025 12:28:07 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[project_approvers](
	[project_id] [int] NOT NULL,
	[user_id] [int] NOT NULL,
 CONSTRAINT [PK_dbo.project_approvers] PRIMARY KEY CLUSTERED 
(
	[project_id] ASC,
	[user_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[project_approvers]  WITH CHECK ADD  CONSTRAINT [FK_dbo.project_approvers_dbo.projects_project_id] FOREIGN KEY([project_id])
REFERENCES [dbo].[projects] ([project_id])
ON DELETE CASCADE
GO

ALTER TABLE [dbo].[project_approvers] CHECK CONSTRAINT [FK_dbo.project_approvers_dbo.projects_project_id]
GO

ALTER TABLE [dbo].[project_approvers]  WITH CHECK ADD  CONSTRAINT [FK_project_approvers_Employee_user_id] FOREIGN KEY([user_id])
REFERENCES [dbo].[Employee] ([EmpId])
GO

ALTER TABLE [dbo].[project_approvers] CHECK CONSTRAINT [FK_project_approvers_Employee_user_id]
GO


USE [att_db]
GO

/****** Object:  Table [dbo].[projects]    Script Date: 12/1/2025 12:28:19 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[projects](
	[project_id] [int] IDENTITY(1,1) NOT NULL,
	[project_name] [nvarchar](max) NOT NULL,
	[client_name] [nvarchar](max) NULL,
	[start_date] [datetime] NULL,
	[end_date] [datetime] NULL,
	[status] [nvarchar](max) NULL,
	[project_number] [nvarchar](50) NULL,
	[planned_hours] [int] NULL,
	[DepId] [int] NULL,
	[is_billable] [bit] NOT NULL,
 CONSTRAINT [PK_dbo.projects] PRIMARY KEY CLUSTERED 
(
	[project_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[projects] ADD  DEFAULT ((1)) FOR [is_billable]
GO

ALTER TABLE [dbo].[projects]  WITH CHECK ADD  CONSTRAINT [FK_projects_Department] FOREIGN KEY([DepId])
REFERENCES [dbo].[Department] ([DepId])
GO

ALTER TABLE [dbo].[projects] CHECK CONSTRAINT [FK_projects_Department]
GO



USE [att_db]
GO

/****** Object:  Table [dbo].[tasks]    Script Date: 12/1/2025 12:28:41 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[tasks](
	[task_id] [int] IDENTITY(1,1) NOT NULL,
	[task_name] [nvarchar](max) NOT NULL,
	[description] [nvarchar](max) NULL,
	[created_by] [int] NULL,
	[project_id] [int] NOT NULL,
	[created_at] [datetime] NOT NULL,
	[TaskTypeId] [int] NOT NULL,
 CONSTRAINT [PK_dbo.tasks] PRIMARY KEY CLUSTERED 
(
	[task_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[tasks]  WITH CHECK ADD  CONSTRAINT [FK_dbo.tasks_dbo.projects_project_id] FOREIGN KEY([project_id])
REFERENCES [dbo].[projects] ([project_id])
ON DELETE CASCADE
GO

ALTER TABLE [dbo].[tasks] CHECK CONSTRAINT [FK_dbo.tasks_dbo.projects_project_id]
GO

ALTER TABLE [dbo].[tasks]  WITH CHECK ADD  CONSTRAINT [FK_tasks_Employee_created_by] FOREIGN KEY([created_by])
REFERENCES [dbo].[Employee] ([EmpId])
GO

ALTER TABLE [dbo].[tasks] CHECK CONSTRAINT [FK_tasks_Employee_created_by]
GO

ALTER TABLE [dbo].[tasks]  WITH CHECK ADD  CONSTRAINT [FK_tasks_TaskTypes] FOREIGN KEY([TaskTypeId])
REFERENCES [dbo].[TaskTypes] ([TaskTypeId])
GO

ALTER TABLE [dbo].[tasks] CHECK CONSTRAINT [FK_tasks_TaskTypes]
GO


USE [att_db]
GO

/****** Object:  Table [dbo].[TaskTypes]    Script Date: 12/1/2025 12:29:00 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[TaskTypes](
	[TaskTypeId] [int] IDENTITY(1,1) NOT NULL,
	[TaskTypeName] [nvarchar](100) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[TaskTypeId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO


USE [att_db]
GO

/****** Object:  Table [dbo].[timesheet_entries]    Script Date: 12/1/2025 12:29:10 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[timesheet_entries](
	[entry_id] [int] IDENTITY(1,1) NOT NULL,
	[user_id] [int] NOT NULL,
	[project_id] [int] NOT NULL,
	[task_id] [int] NULL,
	[week_start_date] [datetime] NOT NULL,
	[monday_hours] [decimal](18, 2) NULL,
	[tuesday_hours] [decimal](18, 2) NULL,
	[wednesday_hours] [decimal](18, 2) NULL,
	[thursday_hours] [decimal](18, 2) NULL,
	[friday_hours] [decimal](18, 2) NULL,
	[saturday_hours] [decimal](18, 2) NULL,
	[sunday_hours] [decimal](18, 2) NULL,
	[status] [nvarchar](max) NOT NULL,
	[notes] [nvarchar](max) NULL,
	[created_at] [datetime] NOT NULL,
	[updated_at] [datetime] NOT NULL,
	[total_hours]  AS ((((((coalesce([monday_hours],(0))+coalesce([tuesday_hours],(0)))+coalesce([wednesday_hours],(0)))+coalesce([thursday_hours],(0)))+coalesce([friday_hours],(0)))+coalesce([saturday_hours],(0)))+coalesce([sunday_hours],(0))) PERSISTED,
	[AssignmentId] [int] NULL,
 CONSTRAINT [PK_dbo.timesheet_entries] PRIMARY KEY CLUSTERED 
(
	[entry_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[timesheet_entries]  WITH CHECK ADD  CONSTRAINT [FK_dbo.timesheet_entries_dbo.projects_project_id] FOREIGN KEY([project_id])
REFERENCES [dbo].[projects] ([project_id])
GO

ALTER TABLE [dbo].[timesheet_entries] CHECK CONSTRAINT [FK_dbo.timesheet_entries_dbo.projects_project_id]
GO

ALTER TABLE [dbo].[timesheet_entries]  WITH CHECK ADD  CONSTRAINT [FK_dbo.timesheet_entries_dbo.tasks_task_id] FOREIGN KEY([task_id])
REFERENCES [dbo].[tasks] ([task_id])
GO

ALTER TABLE [dbo].[timesheet_entries] CHECK CONSTRAINT [FK_dbo.timesheet_entries_dbo.tasks_task_id]
GO

ALTER TABLE [dbo].[timesheet_entries]  WITH CHECK ADD  CONSTRAINT [FK_timesheet_entries_Assignments] FOREIGN KEY([AssignmentId])
REFERENCES [dbo].[Assignments] ([AssignmentId])
GO

ALTER TABLE [dbo].[timesheet_entries] CHECK CONSTRAINT [FK_timesheet_entries_Assignments]
GO

ALTER TABLE [dbo].[timesheet_entries]  WITH CHECK ADD  CONSTRAINT [FK_timesheet_entries_Employee_user_id] FOREIGN KEY([user_id])
REFERENCES [dbo].[Employee] ([EmpId])
GO

ALTER TABLE [dbo].[timesheet_entries] CHECK CONSTRAINT [FK_timesheet_entries_Employee_user_id]
GO

USE [att_db]
GO

/****** Object:  Table [dbo].[UserType]    Script Date: 12/1/2025 12:29:50 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[UserType](
	[UserTypeId] [int] NOT NULL,
	[UserTypeName] [nvarchar](50) NOT NULL,
 CONSTRAINT [PK_UserType] PRIMARY KEY CLUSTERED 
(
	[UserTypeId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

USE [att_db]
GO

/****** Object:  Table [dbo].[Vacation]    Script Date: 12/1/2025 12:31:24 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Vacation](
	[VacationId] [int] IDENTITY(1,1) NOT NULL,
	[VacationDesc] [nvarchar](max) NULL,
	[VacationTypeId] [int] NOT NULL,
	[EmpId] [int] NOT NULL,
	[IsAccepted] [bit] NULL,
	[From] [date] NOT NULL,
	[To] [date] NOT NULL,
	[DateOfRequestingVacation] [date] NOT NULL,
	[IsMedical] [bit] NULL,
	[IsCancel] [bit] NULL,
	[Qouta] [float] NULL,
	[Attachment] [image] NULL,
 CONSTRAINT [PK_Vacation] PRIMARY KEY CLUSTERED 
(
	[VacationId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[Vacation]  WITH CHECK ADD  CONSTRAINT [FK_Vacation_Employee1] FOREIGN KEY([EmpId])
REFERENCES [dbo].[Employee] ([EmpId])
GO

ALTER TABLE [dbo].[Vacation] CHECK CONSTRAINT [FK_Vacation_Employee1]
GO

ALTER TABLE [dbo].[Vacation]  WITH CHECK ADD  CONSTRAINT [FK_Vacation_VacationType] FOREIGN KEY([VacationTypeId])
REFERENCES [dbo].[VacationType] ([VacationTypeId])
GO

ALTER TABLE [dbo].[Vacation] CHECK CONSTRAINT [FK_Vacation_VacationType]
GO

