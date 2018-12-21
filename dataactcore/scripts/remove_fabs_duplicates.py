import logging

from dataactcore.interfaces.db import GlobalDB
from dataactcore.logging import configure_logging
from dataactvalidator.health_check import create_app

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    """ Cleans up duplicated FABS published records and unpublishes the submissions they're associated with if all
        records from a specific submission are deleted.
    """

    with create_app().app_context():
        configure_logging()

        sess = GlobalDB.db().session

        # Create a temporary table
        sess.execute("""CREATE TEMP TABLE duplicated_fabs AS
                            SELECT afa_generated_unique, MAX(submission_id) AS max_id
                            FROM published_award_financial_assistance
                            WHERE is_active IS TRUE
                            GROUP BY afa_generated_unique
                            HAVING COUNT(1) > 1""")

        # Figure out exactly which submissions have been affected in any way
        executed = sess.execute(""" SELECT DISTINCT submission_id
                                    FROM published_award_financial_assistance AS pafa
                                    WHERE is_active IS TRUE
                                    AND EXISTS (SELECT 1
                                                FROM duplicated_fabs AS df
                                                WHERE df.afa_generated_unique = pafa.afa_generated_unique)""")
        affected_submissions = []
        for row in executed:
            affected_submissions.append(row['submission_id'])

        # If no rows are affected, just exit, no need to hit the DB anymore
        if len(affected_submissions) == 0:
            logger.info("There are no duplicated submissions, ending script.")
            exit(0)

        # Delete duplicates from the published FABS table, keeping the instance with the highest submission_id
        executed = sess.execute(""" DELETE FROM published_award_financial_assistance AS pafa
                                    WHERE is_active IS TRUE
                                        AND EXISTS (SELECT 1
                                            FROM duplicated_fabs AS df
                                            WHERE df.afa_generated_unique = pafa.afa_generated_unique
                                                AND df.max_id != pafa.submission_id)""")

        logger.info("Deleted {} duplicate rows from published_award_financial_assistance".format(executed.rowcount))

        # Make a list of submissions that have had all published records deleted
        cleared_submissions = []
        for sub in affected_submissions:
            executed = sess.execute(""" SELECT COUNT(*) as result_count
                                        FROM published_award_financial_assistance
                                        WHERE submission_id = {}""".format(sub))
        # sess.commit()
