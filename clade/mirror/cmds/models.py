# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Paths(models.Model):
    path = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'paths'


class Cmds(models.Model):
    pid = models.IntegerField(blank=True, null=True)
    cwd = models.ForeignKey('Paths', models.DO_NOTHING, related_name='cwd_ids', blank=True, null=True)
    which = models.ForeignKey('Paths', models.DO_NOTHING, related_name='which_ids', blank=True, null=True)
    command = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'cmds'


class ParsedCmds(models.Model):
    id = models.ForeignKey(Cmds, models.DO_NOTHING, db_column='id', primary_key=True)
    type = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'parsed_cmds'


class CmdGraph(models.Model):
    cmd_id = models.ForeignKey('ParsedCmds', models.DO_NOTHING, db_column='cmd_id', related_name='cmd_ids', blank=True, null=True)
    used_by = models.ForeignKey('ParsedCmds', models.DO_NOTHING, db_column='used_by', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cmd_graph'


class CmdIn(models.Model):
    cmd_id = models.ForeignKey('ParsedCmds', models.DO_NOTHING, db_column='cmd_id', blank=True, null=True)
    in_id = models.ForeignKey('Paths', models.DO_NOTHING, db_column='in_id', blank=True, null=True)  # Field renamed because it was a Python reserved word.

    class Meta:
        managed = False
        db_table = 'cmd_in'


class CmdOpts(models.Model):
    id = models.ForeignKey('ParsedCmds', models.DO_NOTHING, db_column='id', primary_key=True)
    opts = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'cmd_opts'


class CmdOut(models.Model):
    cmd_id = models.ForeignKey('ParsedCmds', models.DO_NOTHING, db_column='cmd_id', blank=True, null=True)
    out_id = models.ForeignKey('Paths', models.DO_NOTHING, db_column='out_id', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cmd_out'


class SrcCompiledIn(models.Model):
    path_id = models.ForeignKey(Paths, models.DO_NOTHING, db_column='path_id', blank=True, null=True)
    cmd_id = models.ForeignKey(ParsedCmds, models.DO_NOTHING, db_column='cmd_id', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'src_compiled_in'


class SrcUsedBy(models.Model):
    path_id = models.ForeignKey(Paths, models.DO_NOTHING, db_column='path_id', blank=True, null=True)
    cmd_id = models.ForeignKey(ParsedCmds, models.DO_NOTHING, db_column='cmd_id', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'src_used_by'
