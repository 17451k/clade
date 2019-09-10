from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Cmds, ParsedCmds, CmdIn, CmdOut


def cmds(request):
    cmds = Cmds.objects.order_by('id')

    # parse GET parameters
    cmd_id_filter = request.GET.get('cmd_id', '')
    cmd_pid_filter = request.GET.get('cmd_pid', '')
    which_filter = request.GET.get('which', '')
    command_filter = request.GET.get('command', '')
    parsed_only = request.GET.get('parsed_only', 'off')

    parsed_ids = ParsedCmds.objects.all().values_list('id', flat=True)

    if parsed_only == 'on':
        cmds = cmds.filter(id__in=parsed_ids)
        parsed_checked = 'checked'
    else:
        parsed_checked = ''

    if cmd_id_filter:
        cmd_id_filter = cmd_id_filter.replace(' ', '')
        cmd_id_list = cmd_id_filter.split(',')
        cmds = cmds.filter(id__in=cmd_id_list)

    if cmd_pid_filter:
        cmd_pid_filter = cmd_pid_filter.replace(' ', '')
        cmd_pid_list = cmd_pid_filter.split(',')
        cmds = cmds.filter(pid__in=cmd_pid_list)

    if which_filter:
        cmds = cmds.filter(which__path__regex=which_filter)

    if command_filter:
        cmds = cmds.filter(command__regex=command_filter)

    # setup pagination
    page_length = 100
    paginator = Paginator(cmds, page_length)

    page = request.GET.get('page')
    cmds = paginator.get_page(page)

    for cmd in cmds:
        if cmd.id in parsed_ids:
            cmd.tr_class = 'parsed'
        else:
            cmd.tr_class = 'unparsed'

        cmd.pid_href = '{}#{}'.format((cmd.pid - 1) // page_length + 1, cmd.pid)

    request_params = {
        'cmds': cmds,
        'base_href': '?cmd_id_filter={}&cmd_pid_filter={}&which={}&command={}&parsed_only={}'.format(cmd_id_filter, cmd_pid_filter, which_filter, command_filter, parsed_only),
        'cmd_id_filter': cmd_id_filter,
        'cmd_pid_filter': cmd_pid_filter,
        'which_filter': which_filter,
        'command_filter': command_filter,
        'parsed_checked': parsed_checked
    }

    return render(request, 'cmds/cmds.html', request_params)


def cmd(request, cmd_id):
    cmd_obj = get_object_or_404(Cmds, pk=cmd_id)

    cmd_in_objs = CmdIn.objects.filter(cmd_id__exact=cmd_id)
    cmd_ins = [obj.in_id.path for obj in cmd_in_objs]

    cmd_out_objs = CmdOut.objects.filter(cmd_id__exact=cmd_id)
    cmd_outs = [obj.out_id.path for obj in cmd_out_objs]

    try:
        cmd_type = ParsedCmds.objects.get(pk=cmd_id).type
    except ParsedCmds.DoesNotExist:
        cmd_type = '-'

    temp_vars = {
        'cmd_id': cmd_id,
        'cmd_pid': cmd_obj.pid,
        'cmd_type': cmd_type,
        'cmd_cwd': cmd_obj.cwd.path,
        'cmd_which': cmd_obj.which.path,
        'cmd_raw': cmd_obj.command,
        'cmd_ins': cmd_ins,
        'cmd_outs': cmd_outs
    }
    return render(request, 'cmds/cmd.html', temp_vars)


def pid_graph(request, cmd_id):
    return render(request, 'cmds/pid_graph.html', {'cmd_id': cmd_id})


def pid_graph_lazy(request, cmd_id):
    return render(request, 'cmds/pid_graph_lazy.html', {'cmd_id': cmd_id})


def get_graph_node(cmd_id, depth=None):
    if depth:
        depth -= 1

    cmd_obj = Cmds.objects.get(pk=cmd_id)
    which = cmd_obj.which.path

    data = {
        "name": "[{}] {}".format(cmd_id, which),
        "id": cmd_id
    }

    if depth is not None and depth <= 0:
        return data

    child_objs = Cmds.objects.filter(pid__exact=cmd_id)
    child_ids = [obj.id for obj in child_objs]

    if child_ids:
        data["children"] = []

    for child_id in child_ids:
        data["children"].append(get_graph_node(child_id, depth=depth))

    return data


def load_pid_graph(request, cmd_id):
    data = get_graph_node(cmd_id)

    return JsonResponse(data, safe=False)


def load_pid_graph_lazy(request, cmd_id):
    data = get_graph_node(cmd_id, depth=2)

    return JsonResponse(data, safe=False)


def load_pid_graph_node(request, cmd_id):
    data = get_graph_node(cmd_id, depth=2)
    proper_data = {data["name"]: data.get("children", None)}

    return JsonResponse(proper_data, safe=False)


def cmd_graph(request, cmd_id):
    return render(request, 'cmds/cmd_graph.html', {'cmd_id': cmd_id})


def load_cmd_graph(request, cmd_id):
    data = get_cmd_graph_node(cmd_id)

    return JsonResponse(data, safe=False)


def get_cmd_graph_node(cmd_id, depth=None):
    if depth:
        depth -= 1

    cmd_obj = Cmds.objects.get(pk=cmd_id)

    data = dict()
    data = {
        "name": "[{}] {}".format(cmd_id, which),
        "id": cmd_id
    }

    if depth is not None and depth <= 0:
        return data

    child_objs = Cmds.objects.filter(pid__exact=cmd_id)
    child_ids = [obj.id for obj in child_objs]

    if child_ids:
        data["children"] = []

    for child_id in child_ids:
        data["children"].append(get_graph_node(child_id, depth=depth))

    return data
