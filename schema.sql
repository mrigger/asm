CREATE TABLE `ApplicationCategory` (
	`ID`	INTEGER,
	`NAME`	TEXT,
	`SUPER_ID`	INTEGER,
	PRIMARY KEY(`ID`),
	FOREIGN KEY(`SUPER_ID`) REFERENCES ApplicationCategory(ID)
);
CREATE TABLE `ApplicationCategoriesPerProject` (
	`ApplicationCategoryID`	INTEGER NOT NULL,
	`GithubProjectID`	INTEGER NOT NULL,
	FOREIGN KEY(`ApplicationCategoryID`) REFERENCES ApplicationCategory(ID)
	FOREIGN KEY(`GithubProjectID`) REFERENCES GithubProject(ID)
);
CREATE TABLE `AsmUsageCategory` (
	`ID`	INTEGER,
	`NAME`	TEXT,
	`SUPER_ID`	INTEGER,
	PRIMARY KEY(`ID`),
	FOREIGN KEY(`SUPER_ID`) REFERENCES AsmUsageCategory(ID)
);
CREATE TABLE `AsmInstruction` (
	`ID`	INTEGER,
	`INSTRUCTION`	TEXT NOT NULL,
	`TEST_CASE`	TEXT NOT NULL,
	PRIMARY KEY(`ID`)
);
CREATE TABLE `AsmSequence` (
	`ID`	INTEGER,
	`COMPOUND_TEST_CASE`	TEXT,
	`NOTE`	TEXT,
	PRIMARY KEY(`ID`)
);
CREATE TABLE `AsmSequenceInstruction` (
	`INSTRUCTION_NUMBER`	INTEGER,
	`ASM_SEQUENCE_ID`	INTEGER,
	`ASM_INSTRUCTION_ID`	INTEGER,
	FOREIGN KEY(`ASM_SEQUENCE_ID`) REFERENCES AsmSequence(ID)
	FOREIGN KEY(`ASM_INSTRUCTION_ID`) REFERENCES AsmSequence(ID)
);
CREATE TABLE `AsmSequencesInGithubProject` (
	`IN_FILE`	STRING NOT NULL,
	`USAGE_COMMENT`	TEXT,
	`INLINE_ASSEMBLY`	INTEGER,
	`HAS_FALLBACK`	INTEGER DEFAULT 'uninvestigated',
	`GITHUB_PROJECT_ID`	INTEGER,
	`ASM_SEQUENCE_ID`	INTEGER,
	FOREIGN KEY(`GITHUB_PROJECT_ID`) REFERENCES GithubProject(ID)
	FOREIGN KEY(`ASM_SEQUENCE_ID`) REFERENCES AsmSequence(ID)
);
CREATE TABLE `AsmUsageCategoryPerSequence` (
	`ASM_USAGE_CATEGORY_ID`	INTEGER,
	`ASM_SEQUENCE_ID`	INTEGER,
	FOREIGN KEY(`ASM_USAGE_CATEGORY_ID`) REFERENCES AsmUsageCategory(ID)
	FOREIGN KEY(`ASM_SEQUENCE_ID`) REFERENCES AsmSequence(ID)
);
CREATE TABLE "GithubProject" (
	`ID`	INTEGER,
	`GITHUB_PROJECT_NAME`	TEXT NOT NULL,
	`GITHUB_URL`	TEXT NOT NULL UNIQUE,
	`GITHUB_DESCRIPTION`	TEXT NOT NULL,
	`GITHUB_NR_STARGAZERS`	INTEGER NOT NULL,
	`GITHUB_NR_SUBSCRIBERS`	INTEGER NOT NULL,
	`GITHUB_NR_FORKS`	INTEGER NOT NULL,
	`GITHUB_NR_OPEN_ISSUES`	INTEGER NOT NULL,
	`GITHUB_REPO_CREATION_DATE`	TEXT NOT NULL,
	`GITHUB_LANGUAGE`	TEXT NOT NULL,
	`PULL_HASH`	TEXT NOT NULL,
	`PULL_DATE`	TEXT NOT NULL,
	`CLOC_LOC_C`	INTEGER NOT NULL,
	`CLOC_LOC_H`	INTEGER NOT NULL,
	`CLOC_LOC_ASSEMBLY`	INTEGER NOT NULL,
	`CLOC_LOC_CPP`	INTEGER NOT NULL,
	`GIT_NR_COMMITS`	INTEGER NOT NULL,
	`GIT_NR_COMMITTERS`	INTEGER NOT NULL,
	`GIT_FIRST_COMMIT_DATE`	TEXT NOT NULL,
	`GIT_LAST_COMMIT_DATE`	TEXT NOT NULL,
	`MANUALLY_CHECKED`	INTEGER NOT NULL DEFAULT 0,
	`ANALYZED_FOR_INLINE_ASM`	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY(`ID`)
);
