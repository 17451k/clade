#ifndef ENV_H
#define ENV_H

extern char **copy_envp(char **);
extern char **update_envp(char **);
extern void update_environ(char **);

extern char *get_parent_id();

#endif /* ENV_H */
