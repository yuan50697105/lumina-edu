-- ============================================
-- Lumina 墨光 · MySQL 9.7 初始化脚本
-- 单体应用 create_all 会自动建表；本脚本供 compose
-- /docker-entrypoint-initdb.d 或生产环境初始化使用。
-- 由 app/models.py（SQLAlchemy）自动生成，勿手工编辑；
-- 重新生成：python 部署/scripts/gen_init_sql.py
-- ============================================


CREATE TABLE ai_conversations (
	id CHAR(36) NOT NULL, 
	user_id CHAR(36) NOT NULL, 
	title VARCHAR(200), 
	model VARCHAR(50), 
	context_course_id CHAR(36), 
	context_chapter_id CHAR(36), 
	message_count INTEGER, 
	total_tokens INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME DEFAULT now(), 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_ai_conversations_user_id ON ai_conversations (user_id);


CREATE TABLE ai_providers (
	id CHAR(36) NOT NULL, 
	name VARCHAR(30) NOT NULL, 
	display_name VARCHAR(50) NOT NULL, 
	description VARCHAR(200), 
	domain VARCHAR(200), 
	endpoint_base VARCHAR(300), 
	enabled BOOL, 
	monthly_quota NUMERIC(12, 2), 
	used_quota NUMERIC(12, 2), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE api_logs (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	method VARCHAR(10) NOT NULL, 
	path VARCHAR(500) NOT NULL, 
	status_code INTEGER, 
	duration_ms INTEGER, 
	user_id CHAR(36), 
	request_id VARCHAR(100), 
	error_message TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
)

;


CREATE TABLE courses (
	id CHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	teacher_id CHAR(36) NOT NULL, 
	credits NUMERIC(3, 1), 
	semester VARCHAR(20) NOT NULL, 
	status VARCHAR(20), 
	code VARCHAR(20) NOT NULL, 
	description TEXT, 
	department VARCHAR(100), 
	schedule JSON, 
	students_count INTEGER, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (code)
)

;


CREATE TABLE event_tracking (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	event_name VARCHAR(100) NOT NULL, 
	user_id CHAR(36), 
	session_id VARCHAR(100), 
	course_id CHAR(36), 
	properties JSON, 
	page_url VARCHAR(500), 
	user_agent TEXT, 
	ip_address VARCHAR(45), 
	created_at DATETIME, 
	PRIMARY KEY (id)
)

;


CREATE TABLE users (
	id CHAR(36) NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	student_id VARCHAR(20), 
	avatar_url VARCHAR(500), 
	`role` VARCHAR(20) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	department VARCHAR(100), 
	grade VARCHAR(10), 
	bio TEXT, 
	last_login_at DATETIME, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (student_id), 
	UNIQUE (email)
)

;


CREATE TABLE ai_messages (
	id CHAR(36) NOT NULL, 
	conversation_id CHAR(36) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	content TEXT, 
	attachments JSON, 
	prompt_tokens INTEGER, 
	completion_tokens INTEGER, 
	latency_ms INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES ai_conversations (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_ai_messages_conversation_id ON ai_messages (conversation_id);


CREATE TABLE ai_models (
	id CHAR(36) NOT NULL, 
	provider_id CHAR(36) NOT NULL, 
	model_name VARCHAR(50) NOT NULL, 
	display_name VARCHAR(50) NOT NULL, 
	task_types JSON, 
	description VARCHAR(200), 
	enabled BOOL, 
	priority INTEGER, 
	cost_per_1k_tokens NUMERIC(8, 4), 
	max_tokens INTEGER, 
	api_style VARCHAR(20), 
	openai_compatible BOOL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES ai_providers (id), 
	UNIQUE (model_name)
)

;


CREATE TABLE announcements (
	id CHAR(36) NOT NULL, 
	course_id CHAR(36) NOT NULL, 
	author_id CHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content TEXT, 
	pinned BOOL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)

;


CREATE TABLE assignments (
	id CHAR(36) NOT NULL, 
	course_id CHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	due_at DATETIME, 
	max_score INTEGER, 
	ai_grading BOOL, 
	rubric JSON, 
	ai_model VARCHAR(50), 
	status VARCHAR(20), 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)

;


CREATE TABLE chapters (
	id CHAR(36) NOT NULL, 
	course_id CHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content TEXT, 
	order_num INTEGER, 
	resources JSON, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)

;


CREATE TABLE enrollments (
	id CHAR(36) NOT NULL, 
	user_id CHAR(36) NOT NULL, 
	course_id CHAR(36) NOT NULL, 
	`role` VARCHAR(20), 
	enrolled_at DATETIME NOT NULL DEFAULT now(), 
	status VARCHAR(20), 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)COMMENT='选课记录，UNIQUE(user_id, course_id) 在外部索引保证'

;


CREATE TABLE grade_records (
	id CHAR(36) NOT NULL, 
	student_id CHAR(36) NOT NULL, 
	course_id CHAR(36) NOT NULL, 
	semester VARCHAR(20) NOT NULL, 
	final_score NUMERIC(5, 2), 
	gpa_point NUMERIC(3, 2), 
	recorded_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_grade_record UNIQUE (student_id, course_id, semester), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)

;


CREATE TABLE live_rooms (
	id CHAR(36) NOT NULL, 
	course_id CHAR(36) NOT NULL, 
	teacher_id CHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	status VARCHAR(20), 
	stream_key VARCHAR(100), 
	viewer_count INTEGER, 
	active_call JSON, 
	started_at DATETIME, 
	ended_at DATETIME, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)

;


CREATE TABLE sessions (
	id CHAR(36) NOT NULL, 
	user_id CHAR(36) NOT NULL, 
	refresh_token VARCHAR(500) NOT NULL, 
	device VARCHAR(20), 
	ip_address VARCHAR(45), 
	user_agent TEXT, 
	expires_at DATETIME NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (refresh_token)
)

;


CREATE TABLE ai_call_logs (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	user_id CHAR(36), 
	model_id CHAR(36) NOT NULL, 
	model_name VARCHAR(50) NOT NULL, 
	task_type VARCHAR(20) NOT NULL, 
	prompt_tokens INTEGER, 
	completion_tokens INTEGER, 
	latency_ms INTEGER, 
	cost NUMERIC(10, 4), 
	ok BOOL, 
	error_message TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(model_id) REFERENCES ai_models (id)
)

;


CREATE TABLE live_attendees (
	id CHAR(36) NOT NULL, 
	room_id CHAR(36) NOT NULL, 
	user_id CHAR(36) NOT NULL, 
	`role` VARCHAR(20), 
	joined_at DATETIME NOT NULL DEFAULT now(), 
	left_at DATETIME, 
	raise_hand BOOL, 
	raised_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_live_attendee UNIQUE (room_id, user_id), 
	FOREIGN KEY(room_id) REFERENCES live_rooms (id) ON DELETE CASCADE
)

;


CREATE TABLE live_messages (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	room_id CHAR(36) NOT NULL, 
	user_id CHAR(36), 
	msg_type VARCHAR(20), 
	content TEXT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(room_id) REFERENCES live_rooms (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_live_messages_room_id ON live_messages (room_id);


CREATE TABLE live_quizzes (
	id CHAR(36) NOT NULL, 
	room_id CHAR(36) NOT NULL, 
	teacher_id CHAR(36) NOT NULL, 
	question TEXT NOT NULL, 
	options JSON NOT NULL, 
	answer VARCHAR(10), 
	status VARCHAR(20), 
	created_at DATETIME NOT NULL DEFAULT now(), 
	closed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(room_id) REFERENCES live_rooms (id) ON DELETE CASCADE
)

;


CREATE TABLE submissions (
	id CHAR(36) NOT NULL, 
	assignment_id CHAR(36) NOT NULL, 
	student_id CHAR(36) NOT NULL, 
	file_urls JSON, 
	text_answer TEXT, 
	submission_note TEXT, 
	submitted_at DATETIME NOT NULL DEFAULT now(), 
	late BOOL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(assignment_id) REFERENCES assignments (id) ON DELETE CASCADE
)

;


CREATE TABLE grades (
	id CHAR(36) NOT NULL, 
	submission_id CHAR(36) NOT NULL, 
	total_score NUMERIC(5, 2), 
	grade_letter VARCHAR(2), 
	feedback TEXT, 
	rubric_scores JSON, 
	graded_by VARCHAR(20), 
	grader_id CHAR(36), 
	ai_model VARCHAR(50), 
	confidence NUMERIC(3, 2), 
	graded_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (submission_id), 
	FOREIGN KEY(submission_id) REFERENCES submissions (id) ON DELETE CASCADE
)

;


CREATE TABLE live_quiz_answers (
	id CHAR(36) NOT NULL, 
	quiz_id CHAR(36) NOT NULL, 
	user_id CHAR(36) NOT NULL, 
	choice VARCHAR(10) NOT NULL, 
	submitted_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_quiz_answer UNIQUE (quiz_id, user_id), 
	FOREIGN KEY(quiz_id) REFERENCES live_quizzes (id) ON DELETE CASCADE
)

;

