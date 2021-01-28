#ifndef ENV_H
#define ENV_H

extern char **update_envp(char **input_envp);
extern void update_environ(char **envp);

extern char *get_parent_id();
extern int get_cmd_id();

extern char *getenv_or_fail(const char *name);

// All environment variables used by clade
#define CLADE_INTERCEPT_OPEN_ENV "CLADE_INTERCEPT_OPEN"
#define CLADE_INTERCEPT_EXEC_ENV "CLADE_INTERCEPT"
#define CLADE_ID_FILE_ENV "CLADE_ID_FILE"
#define CLADE_PARENT_ID_ENV "CLADE_PARENT_ID"
#define CLADE_UNIX_ADDRESS_ENV "CLADE_UNIX_ADDRESS"
#define CLADE_INET_HOST_ENV "CLADE_INET_HOST"
#define CLADE_INET_PORT_ENV "CLADE_INET_PORT"
#define CLADE_PREPROCESS_ENV "CLADE_PREPROCESS"
// Do not forget to add new variables to clade_envs inside env.c

#endif /* ENV_H */
