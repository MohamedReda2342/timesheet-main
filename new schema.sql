-- ==============================================
-- USERS
-- ==============================================
CREATE TABLE `users` (
  `user_id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(100) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('user','approver','admin') NOT NULL DEFAULT 'user',
  `full_name` VARCHAR(255) DEFAULT NULL,
  `email` VARCHAR(255) DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`)
);

-- ==============================================
-- PROJECTS
-- ==============================================
CREATE TABLE `projects` (
  `project_id` INT NOT NULL AUTO_INCREMENT,
  `project_name` VARCHAR(255) NOT NULL,
  `client_name` VARCHAR(255) DEFAULT NULL,
  `start_date` DATE DEFAULT NULL,
  `end_date` DATE DEFAULT NULL,
  `status` ENUM('active','on-hold','completed') DEFAULT 'active',
  PRIMARY KEY (`project_id`)
);

-- ==============================================
-- TASKS
-- ==============================================
CREATE TABLE `tasks` (
  `task_id` INT NOT NULL AUTO_INCREMENT,
  `task_name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `created_by` INT,
  `project_id` INT NOT NULL,
  `is_billable` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  KEY `project_id` (`project_id`),
  CONSTRAINT `fk_tasks_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tasks_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`)
);

-- ==============================================
-- USER TASK ASSIGNMENTS
-- ==============================================
CREATE TABLE `user_tasks` (
  `user_task_id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `task_id` INT NOT NULL,
  `assigned_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_user_tasks_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_user_tasks_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`)
);

-- ==============================================
-- PROJECT APPROVERS
-- ==============================================
CREATE TABLE `project_approvers` (
  `project_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  PRIMARY KEY (`project_id`, `user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `fk_project_approver_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_project_approver_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
);

-- ==============================================
-- TIMESHEET ENTRIES
-- ==============================================
CREATE TABLE `timesheet_entries` (
  `entry_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `project_id` INT NOT NULL,
  `task_id` INT DEFAULT NULL,
  `week_start_date` DATE NOT NULL,
  `monday_hours` DECIMAL(5,2) DEFAULT 0,
  `tuesday_hours` DECIMAL(5,2) DEFAULT 0,
  `wednesday_hours` DECIMAL(5,2) DEFAULT 0,
  `thursday_hours` DECIMAL(5,2) DEFAULT 0,
  `friday_hours` DECIMAL(5,2) DEFAULT 0,
  `saturday_hours` DECIMAL(5,2) DEFAULT 0,
  `sunday_hours` DECIMAL(5,2) DEFAULT 0,
  `total_hours` DECIMAL(6,2) GENERATED ALWAYS AS 
      (COALESCE(`monday_hours`,0) + COALESCE(`tuesday_hours`,0) + COALESCE(`wednesday_hours`,0) + 
       COALESCE(`thursday_hours`,0) + COALESCE(`friday_hours`,0) + COALESCE(`saturday_hours`,0) + 
       COALESCE(`sunday_hours`,0)) STORED,
  `status` ENUM('draft','submitted','approved','rejected','locked') NOT NULL DEFAULT 'draft',
  `notes` TEXT,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`entry_id`),
  KEY `user_id` (`user_id`),
  KEY `project_id` (`project_id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `fk_timesheet_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_timesheet_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`),
  CONSTRAINT `fk_timesheet_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`)
);

-- ==============================================
-- APPROVALS
-- ==============================================
CREATE TABLE `approvals` (
  `approval_id` INT NOT NULL AUTO_INCREMENT,
  `entry_id` INT NOT NULL,
  `approver_id` INT NOT NULL,
  `decision` ENUM('approved','rejected') NOT NULL,
  `comment` TEXT,
  `decision_ts` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`approval_id`),
  KEY `entry_id` (`entry_id`),
  KEY `approver_id` (`approver_id`),
  CONSTRAINT `fk_approval_entry` FOREIGN KEY (`entry_id`) REFERENCES `timesheet_entries` (`entry_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_approval_approver` FOREIGN KEY (`approver_id`) REFERENCES `users` (`user_id`)
);

-- ==============================================
-- IMPORTS LOG
-- ==============================================
CREATE TABLE `imports_log` (
  `import_id` INT AUTO_INCREMENT PRIMARY KEY,
  `admin_id` INT NOT NULL,
  `import_type` ENUM('users', 'tasks', 'assignments') NOT NULL,
  `file_name` VARCHAR(255),
  `imported_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_import_admin` FOREIGN KEY (`admin_id`) REFERENCES `users` (`user_id`)
);

-- ==============================================
-- AUDIT LOG
-- ==============================================
CREATE TABLE `audit_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT DEFAULT NULL,
  `action` VARCHAR(255) NOT NULL,
  `details` TEXT,
  `ts` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
);

-- ==============================================
-- LEAVE CALENDAR
-- ==============================================
CREATE TABLE `leave_calendar` (
  `leave_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT DEFAULT NULL,
  `leave_type` ENUM('vacation','public_holiday','other') NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `source` ENUM('HR','manual') DEFAULT 'manual',
  `notes` TEXT,
  PRIMARY KEY (`leave_id`),
  CONSTRAINT `fk_leave_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
);
