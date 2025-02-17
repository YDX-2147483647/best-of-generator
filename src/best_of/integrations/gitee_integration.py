import logging
from os import getenv

import requests
from addict import Dict
from dateutil.parser import parse

from best_of import utils
from best_of.default_config import ENV_GITEE_API_KEY, MIN_PROJECT_DESC_LENGTH
from best_of.integrations.base_integration import BaseIntegration

log = logging.getLogger(__name__)


class GiteeIntegration(BaseIntegration):
    @property
    def name(self) -> str:
        return "gitee"

    def update_project_info(self, project_info: Dict) -> None:
        if not project_info.gitee_id:
            return

        token = getenv(ENV_GITEE_API_KEY)
        if not token:
            log.warning(
                "Gitee projects detected, but no API key provided. "
                "This is fine for lists with few Gitee projects. "
                "Otherwise, please consider generate one at "
                "https://gitee.com/profile/personal_access_tokens"
            )

        try:
            params = Dict()
            if token:
                params.access_token = token

            response = requests.get(
                f"https://gitee.com/api/v5/repos/{project_info.gitee_id}",
                params=params,
            )
            response.raise_for_status()

            repo_info = Dict(response.json())
        except Exception as ex:
            log.info(
                f"Failed to request the repo {project_info.gitee_id} via Gitee API ",
                exc_info=ex,
            )
            return

        if not project_info.gitee_url:
            project_info.gitee_url = repo_info.html_url.removesuffix(".git")

        if not project_info.homepage:
            project_info.homepage = repo_info.homepage or project_info.gitee_url

        if not project_info.name:
            project_info.name = repo_info.name

        if not project_info.license:
            project_info.license = repo_info.license

        if repo_info.description and (
            not project_info.description
            or len(project_info.description) < MIN_PROJECT_DESC_LENGTH
        ):
            project_info.description = repo_info.description

        if repo_info.created_at:
            try:
                created_at = parse(repo_info.created_at, ignoretz=True)
                if not project_info.created_at or project_info.created_at > created_at:
                    project_info.created_at = created_at
            except Exception as ex:
                log.warning(
                    f"Failed to parse timestamp: {repo_info.created_at}",
                    exc_info=ex,
                )

        if repo_info.updated_at:
            try:
                updated_at = parse(repo_info.updated_at, ignoretz=True)
                if not project_info.updated_at or project_info.updated_at < updated_at:
                    project_info.updated_at = updated_at
            except Exception as ex:
                log.warning(
                    f"Failed to parse timestamp: {repo_info.updated_at}",
                    exc_info=ex,
                )

        forks_count = int(repo_info.forks_count) if repo_info.forks_count else 0
        if not project_info.fork_count or int(project_info.fork_count) < forks_count:
            project_info.fork_count = forks_count

        if repo_info.open_issues_count:
            open_issues_count = int(repo_info.open_issues_count)
            if (
                not project_info.open_issue_count
                or int(project_info.open_issue_count) < open_issues_count
            ):
                project_info.open_issue_count = open_issues_count

        if repo_info.stargazers_count:
            stars_count = int(repo_info.stargazers_count)
            if not project_info.star_count or project_info.star_count < stars_count:
                project_info.star_count = stars_count

        if repo_info.watchers_count:
            watchers_count = int(repo_info.watchers_count)
            if (
                not project_info.watchers_count
                or project_info.watchers_count < watchers_count
            ):
                project_info.watchers_count = watchers_count

    def generate_md_details(self, project: Dict, configuration: Dict) -> str:
        # Only show if gitee url is set
        if not project.gitee_id or not project.gitee_url:
            return ""

        metrics_md = ""
        if project.fork_count >= 0:
            if metrics_md:
                metrics_md += " · "
            metrics_md += f"🔀 {utils.simplify_number(project.fork_count)}"

        if project.open_issue_count and project.closed_issue_count:
            if metrics_md:
                metrics_md += " · "
            total_issues = project.closed_issue_count + project.open_issue_count
            metrics_md += (
                f"📋 {utils.simplify_number(total_issues)} - "
                f"{int((project.open_issue_count / total_issues) * 100)}% open"
            )

        if project.updated_at:
            if metrics_md:
                metrics_md += " · "
            metrics_md += f"⏱️ {project.updated_at.strftime('%d.%m.%Y')}"

        if metrics_md:
            metrics_md = f"({metrics_md})"

        separator = (
            ""
            if not configuration.generate_badges
            and not configuration.generate_install_hints
            else ":"
        )

        details_md = f"- [Gitee]({project.gitee_url}) {metrics_md}{separator}\n"

        if configuration.generate_install_hints:
            details_md += f"\n\t```\n\tgit clone {project.gitee_url}\n\t```\n"

        return details_md
