# TODO: Reconsile builders with explicitly set schedulers detection.

from twisted.python import log

from buildbot.plugins import schedulers, util


# Each scheduler listens only for those projects it is interested in.
# Every change comes with a comms-separated list of projects it
# affects, and we want to schedule a build if one of them is
# at interest.
def isProjectOfInterest(cp, projects_of_interest):
    if cp:
        changed_projects = frozenset(cp.split(','))
        if changed_projects.intersection(projects_of_interest):
            return True
    return False


# Since we have many parametric builders, we dynamically build the minimum set
# of schedulers, which covers all actually used combinations of dependencies.
def getMainBranchSchedulers(
    builders,
    explicitly_set_schedulers = None,
    **kwargs):
    """
    I'm taking over all of not yet assigned builders with the
    declared source code dependencies, and automatically generate
    a minimum set of SingleBranchSchedulers to handle all the declared
    source code dependency combinations.
    """

    builders_with_explicit_schedulers = set()
    if explicitly_set_schedulers:
        # TODO: Make a list of builder names with already set schedulers.
        # builders_with_explicit_schedulers.add(builder)
        pass

    # For the builders created with LLVMBuildFactory or similar,
    # we always use automatic schedulers,
    # unless schedulers already explicitly set.
    builders_with_automatic_schedulers = [
        builder for builder in builders
        if builder.name not in builders_with_explicit_schedulers
        if getattr(builder.factory, 'depends_on_projects', None)
        if 'release' not in getattr(builder, 'tags', [])
    ]

    filter_branch = 'main'
    treeStableTimer = kwargs.get('treeStableTimer', None)

    automatic_schedulers = []

    # Do we have any to take care of?
    if builders_with_automatic_schedulers:
        # Let's reconsile first to get a unique set of dependencies.
        # We need a set of unique sets of dependent projects.
        set_of_dependencies = set([
            frozenset(getattr(b.factory, 'depends_on_projects'))
            for b in builders_with_automatic_schedulers
        ])

        for projects in set_of_dependencies:
            main_builders = [
                b.name
                for b in builders_with_automatic_schedulers
                if frozenset(getattr(b.factory, 'depends_on_projects')) == projects
            ]

            automatic_scheduler_name =  filter_branch + ":" + ",".join(sorted(projects))

            automatic_schedulers.append(
                schedulers.SingleBranchScheduler(
                    name=automatic_scheduler_name,
                    treeStableTimer=treeStableTimer,
                    reason="Merge to github {} branch".format(filter_branch),
                    builderNames=main_builders,
                    change_filter=util.ChangeFilter(
                        project_fn= \
                            lambda c, projects_of_interest=frozenset(projects):
                                isProjectOfInterest(c, projects_of_interest),
                        branch=filter_branch)
                )
            )

            log.msg(
                "Generated SingleBranchScheduler: {{ name='{}'".format(automatic_scheduler_name),
                ", builderNames=", main_builders,
                ", change_filter=", projects, " (branch: {})".format(filter_branch),
                ", treeStableTimer={}".format(treeStableTimer),
                "}")
    return automatic_schedulers

def getReleaseBranchSchedulers(
    builders,
    explicitly_set_schedulers = None,
    **kwargs):
    """
    I'm taking over all of not yet assigned builders with the
    declared source code dependencies and the 'release' tag,
    and automatically generate a minimum set of SingleBranchSchedulers
    to handle all the declared source code dependency combinations.
    """

    builders_with_explicit_schedulers = set()
    if explicitly_set_schedulers:
        # TODO: Make a list of builder names with already set schedulers.
        # builders_with_explicit_schedulers.add(builder)
        pass

    # For the builders created with LLVMBuildFactory or similar,
    # we always use automatic schedulers,
    # unless schedulers already explicitly set.
    builders_with_automatic_schedulers = [
        builder for builder in builders
        if builder.name not in builders_with_explicit_schedulers
        if getattr(builder.factory, 'depends_on_projects', None)
        if 'release' in getattr(builder, 'tags', [])
    ]

    treeStableTimer = kwargs.get('treeStableTimer', None)

    automatic_schedulers = []

    # Do we have any to take care of?
    if builders_with_automatic_schedulers:
        # Let's reconsile first to get a unique set of dependencies.
        # We need a set of unique sets of dependent projects.
        set_of_dependencies = set([
            frozenset(getattr(b.factory, 'depends_on_projects'))
            for b in builders_with_automatic_schedulers
        ])

        for projects in set_of_dependencies:
            release_builders = [
                b.name
                for b in builders_with_automatic_schedulers
                if frozenset(getattr(b.factory, 'depends_on_projects')) == projects
            ]

            automatic_scheduler_name =  "release:" + ",".join(sorted(projects))

            automatic_schedulers.append(
                schedulers.SingleBranchScheduler(
                    name=automatic_scheduler_name,
                    treeStableTimer=treeStableTimer,
                    reason="Merge to github release branch",
                    builderNames=release_builders,
                    change_filter=util.ChangeFilter(
                        project_fn= \
                            lambda c, projects_of_interest=frozenset(projects):
                                isProjectOfInterest(c, projects_of_interest),
                        branch_fn= \
                            lambda branch: branch.startswith('release/'))
                )
            )

            log.msg(
                "Generated release SingleBranchScheduler: {{ name='{}'".format(automatic_scheduler_name),
                ", builderNames=", release_builders,
                ", change_filter=", projects, " (branch: {release/*})",
                ", treeStableTimer={}".format(treeStableTimer),
                "}")
    return automatic_schedulers

def getForceSchedulers(builders):
    # TODO: Move these settings to the configuration file.
    _repourl = "https://github.com/llvm/llvm-project"
    _branch = "main"

    # Walk over all builders and collect their names.
    scheduler_builders = [
        builder.name for builder in builders
    ]

    # Create the force schedulers.
    return [ schedulers.ForceScheduler(
                name            = "force-build-scheduler",
                label           = "Force Build",
                buttonName      = "Force Build",
                reason = util.ChoiceStringParameter(
                            name        = "reason",
                            label       = "reason:",
                            required    = True,
                            choices     = [
                                "Build a particular revision",
                                "Force clean build",
                                "Narrow down blamelist",
                            ],
                            default     = "Build a particular revision"
                ),
                builderNames    = scheduler_builders,
                codebases       = [
                    util.CodebaseParameter(
                        codebase    = "",
                        branch      = util.StringParameter(
                            name        = "branch",
                            label       = "branch:",
                            size        = 64,
                            default     = _branch
                        ),
                        revision    = util.StringParameter(
                            name        = "revision",
                            label       = "revision:",
                            size        = 45,
                            default     = ''
                        ),
                        repository  = util.FixedParameter(
                            name        = "repository",
                            default     = _repourl
                        ),
                        project     = util.FixedParameter(
                            name        = "project",
                            default     = "llvm" # All projects depend on llvm
                        )
                    )
                ],
                properties  = [
                    util.BooleanParameter(
                        name        = "clean",
                        label       = "Clean source code and build directory",
                        default     = False
                    ),
                    util.BooleanParameter(
                        name        = "clean_obj",
                        label       = "Clean build directory",
                        default     = False
                    )
                ]
            )
        ]

# TODO: Abstract this kind of scheduler better.
def getLntSchedulers():
    _project = "lnt"
    _branch = 'master'
    _repourl = "https://github.com/llvm/llvm-lnt"
    _lnt_builders = [
        "publish-lnt-sphinx-docs",
    ]
    return [
        schedulers.Nightly(
            name="lnt-scheduler",
            builderNames=_lnt_builders,
            reason='Periodic LNT build',
            hour=1),

        schedulers.ForceScheduler(
            name            = "lnt-force-build-scheduler",
            label           = "Force Build",
            buttonName      = "Force Build",
            reason = util.ChoiceStringParameter(
                         name        = "reason",
                         label       = "reason:",
                         required    = True,
                         choices     = [
                            "Build a particular revision",
                            "Force clean build",
                            "Narrow down blamelist",
                         ],
                         default     = "Build a particular revision"
            ),
            builderNames    = _lnt_builders,
            codebases       = [
                util.CodebaseParameter(
                    codebase    = "",
                    branch          = util.FixedParameter(
                        name        = "branch",
                        default     = _branch
                    ),
                    revision    = util.StringParameter(
                        name        = "revision",
                        label       = "revision:",
                        size        = 45,
                        default     = ''
                    ),
                    repository  = util.FixedParameter(
                        name        = "repository",
                        default     = _repourl
                    ),
                    project     = util.FixedParameter(
                        name        = "project",
                        default     = _project
                    )
                )
            ],
            properties  = [
                util.BooleanParameter(
                    name        = "clean",
                    label       = "Clean source code and build directory",
                    default     = False
                ),
                util.BooleanParameter(
                    name        = "clean_obj",
                    label       = "Clean build directory",
                    default     = False
                )
            ]
        ),
    ]
