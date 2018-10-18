#ifndef ENV_H
#define ENV_H

extern char **update_envp(char **input_envp);
extern void update_environ(char **envp);

extern char *get_parent_id();

#endif /* ENV_H */
