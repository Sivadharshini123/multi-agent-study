# Chapter 1: Queries

<!-- page: 2 -->

The students table keeps one row per learner.

CREATE TABLE students (id INTEGER, name TEXT);
INSERT INTO students VALUES (1, 'Ada');

SELECT name FROM students WHERE id = 1;

This query returns the name for one student id.
A primary key uniquely identifies each row.
A foreign key points at a primary key in another table.
The WHERE clause filters rows before the result is returned.
