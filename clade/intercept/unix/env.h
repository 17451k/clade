#include <stdbool.h>

#ifndef ENV_H
#define ENV_H

extern char **copy_envp(char **envp);
extern char **update_envp(char **input_envp);
extern void update_environ(char **envp, bool force);

extern char *get_parent_id(char **envp);
extern int get_cmd_id();

extern char *getenv_or_fail(const char *name);

char *getenv_from_envp(char **envp, const char *key);
void setenv_to_envp(char **envp, const char *key, const char *value);

// All environment variables used by clade
#define CLADE_INTERCEPT_OPEN_ENV "CLADE_INTERCEPT_OPEN"
#define CLADE_INTERCEPT_EXEC_ENV "CLADE_INTERCEPT"
#define CLADE_ID_FILE_ENV "CLADE_ID_FILE"
#define CLADE_PARENT_ID_ENV "CLADE_PARENT_ID"
#define CLADE_UNIX_ADDRESS_ENV "CLADE_UNIX_ADDRESS"
#define CLADE_INET_HOST_ENV "CLADE_INET_HOST"
#define CLADE_INET_PORT_ENV "CLADE_INET_PORT"
#define CLADE_PREPROCESS_ENV "CLADE_PREPROCESS"
#define CLADE_ENV_VARS_ENV "CLADE_ENV_VARS"
// Do not forget to add new variables to clade_envs inside env.c

#endif /* ENV_H */
