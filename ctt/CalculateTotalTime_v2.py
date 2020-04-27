from jira import JIRA
from jira.resources import Sprint
import pygal
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import requests


def get_date(*keys, **datas):
    return tuple([datetime.strptime(datas[key][:10], '%Y-%m-%d') for key in keys])


def get_sprint_time_range(username, password, sprint_id):
    url = f'https://jira.talendforge.org/rest/agile/1.0/sprint/{sprint_id}'
    response = requests.get(url, auth=(username, password))
    json = response.json()
    return get_date(*('startDate', 'endDate'), **json)


def cal_issue(jira_obj, total_time, issue_key, sprint_start: datetime, sprint_end: datetime):
    print(f'calculating issue={issue_key}....')
    issue_time = {}  # username-time
    # seem the bar can not support multi thread.
    # bar.set_description(f'issue=[{issue_key}]')
    issue_task = jira_obj.issue(issue_key)
    for worklog in issue_task.fields.worklog.worklogs:
        # print(f'{worklog.author.displayName} timeSpent={worklog.timeSpentSeconds}')
        # calculate total time in one issue for each one
        (update_time,) = get_date(*('updated',), updated=worklog.updated)
        if update_time > sprint_start and update_time < sprint_end:
            username = worklog.author.displayName
            time = worklog.timeSpentSeconds / 3600.0  # convert to hour
            if username in issue_time:
                issue_time[username] += time
            else:
                issue_time[username] = time
    #
    for username in issue_time:
        if username in total_time:
            total_time[username].append((issue_key, issue_time[username]))
        else:
            total_time[username] = [(issue_key, issue_time[username])]
    # bar.set_description(f'issue=[{issue_key}]')
    print(f'\t >>issue={issue_key} is done!')


username = 'xqliu'
password = 'MUJ79b@Talend'
board_id = 233
project_name = 'Talend Data Quality'
# 多线程版
if __name__ == '__main__':
    jira_obj = JIRA(basic_auth=(username, password), server='https://jira.talendforge.org')
    thread_count = 10
    # get all sprints
    # MDM board_id=70
    sprints = jira_obj.sprints(board_id=board_id)
    active_sprints = [s for s in sprints if s.state == "ACTIVE"]  # the fureture sprint the state is "FUTURE"
    cur_sprint: Sprint = None
    if len(active_sprints) > 0:
        for sprint in active_sprints:
            # if hasattr(sprint, "goal"):
            if "DQ20 CN 2" in sprint.name:
                cur_sprint = sprint
                print(f'name=[{sprint.name}] id=[{sprint.id}]')
    # output:name=[7.3-MDM-Sprint3] id=[1355] goal=[Jul 26 - Aug 15]
    # sp = jira_obj.sprint(cur_sprint.id)
    # sp_info = jira_obj.sprint_info(70, cur_sprint.id)
    if not cur_sprint:
        print('>> Can not find current active sprint, exit!')
    else:
        sprint_start, sprint_end = get_sprint_time_range(username, password, cur_sprint.id)
        print(f'Querying all issues in current sprint....')
        issues = jira_obj.search_issues(f'Sprint={cur_sprint.id} and  project = "{project_name}"', maxResults=200)
        issue_keys = [i.key for i in issues]
        print(f'Found issues={len(issue_keys)} in {cur_sprint.name}')
        print(f'Thread count={thread_count}')
        total_time = {}  # username -> [(issue,time)]
        # bar = tqdm(issue_keys)
        # process pool
        with ThreadPoolExecutor(thread_count) as executor:
            for issue_key in issue_keys:
                executor.submit(cal_issue, jira_obj, total_time, issue_key, sprint_start, sprint_end)

        user_total_time = {}  # {user,user_total_time}

        for username in total_time:
            total = 0.0
            for (_, time) in total_time[username]:
                total += time
            user_total_time[username] = total
        # sort
        ff = open(f"total_time_summary_{cur_sprint.name}.txt", "w+")
        for (index, (username, total)) in enumerate(
                sorted(user_total_time.items(), key=lambda kv: kv[1], reverse=True)):
            print(f'{index + 1} {username} \t-> total={total} hours')
            ff.write(f'{index + 1} {username} \t-> total={total} hours\r\n')
        ff.close()
        # write result to file
        with open(f"total_time_{cur_sprint.name}.txt", 'w') as f:
            json.dump(total_time, fp=f)
            print(f">> write result to total_time_{cur_sprint.name}.txt")
        # render to chart
        line_chart = pygal.StackedBar(show_legend=False)
        if cur_sprint:
            line_chart.title = f'{cur_sprint.name}'
        xlabels = sorted([user for user in user_total_time], key=lambda kv: kv.lower())

        line_chart.x_labels = xlabels
        temple_value = [None for _ in range(len(total_time))]
        # insert value
        for (index, username) in enumerate(xlabels):
            for (issue, time) in total_time[username]:
                # to create a list like [None, 20, None]
                value = temple_value.copy()
                total_time_str = f'total time:{user_total_time[username]}h'
                link = f'https://jira.talendforge.org/browse/{issue}'
                value[index] = {'value': time, 'label': total_time_str,
                                'xlink': {'href': link, 'target': '_blank'}}
                line_chart.add(issue, value)
        line_chart.render_to_file(f"total_time_{cur_sprint.name}.svg")
        print(f">> generate chart to total_time_{cur_sprint.name}.svg")
