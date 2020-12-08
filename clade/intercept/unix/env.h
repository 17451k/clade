#ifndef ENV_H
#define ENV_H

extern char **update_envp(char **input_envp);
extern void update_environ(char **envp);

extern char *get_parent_id();
extern int get_cmd_id();

extern char *getenv_or_fail(const char *name);

#endif /* ENV_H */
