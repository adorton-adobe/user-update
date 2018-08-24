import argparse
import yaml
import umapi_client
import logging
from umapi_client import IdentityTypes, UserAction
from util import CSVAdapter

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(description='Username Update Tool')
    parser.add_argument('-c', '--config',
                        help='filename of config file',
                        metavar='filename', dest='config_filename')
    parser.add_argument('-u', '--users',
                        help='filename of user file',
                        metavar='filename', dest='users_filename')
    parser.add_argument('-t', '--test-mode',
                        help='run updates in test mode',
                        dest='test_mode',
                        action='store_true',
                        default=False)
    parser.add_argument('-r', '--reverse',
                        help='reverse conversion (go from username to email, rather than email to username)',
                        dest='from_email',
                        action='store_false',
                        default=True)

    args = parser.parse_args()

    with open(args.config_filename, "r") as f:
        config = yaml.load(f)
    conn = umapi_client.Connection(org_id=config["org_id"],
                                   auth_dict=config,
                                   test_mode=args.test_mode,
                                   # ims_host='ims-na1-stg1.adobelogin.com',
                                   ims_endpoint_jwt='/ims/exchange/jwt',
                                   # user_management_endpoint='https://usermanagement-stage.adobe.io/v2/usermanagement',
                                   logger=logger)

    cols = ['Username', 'Email', 'New Email', 'New Username']

    actions = {}
    for user_rec in CSVAdapter.read_csv_rows(args.users_filename, recognized_column_names=cols):
        username, email, new_email, new_username, domain = \
            user_rec.get('Username'), user_rec.get('Email'), user_rec.get('New Email'),user_rec.get('New Username'), user_rec.get('Domain')
        if not username or not email:
            logger.warning("Skipping input record with missing Username and/or Email: %s" % user_rec)
            continue
        try:
            user = UserAction(id_type=IdentityTypes.federatedID, email=username)
            user.update(email=new_email, username=new_username)
            actions[email] = user
            # if args.from_email:
            #     user.update(username=username)
            #     actions[email] = user
            # else:
            #     user.update(username=email)
            #     actions[username] = user
            conn.execute_single(user)
        except Exception as e:
            logger.error("Error with: " + username + " ||| " + 'New Email: ' + new_email)

    conn.execute_queued()

    successes, failures = 0, 0
    for key, action in actions.items():
        if not action.execution_errors():
            successes += 1
        else:
            failures += 1
            logger.error("Conversion of %s failed: %s" % (key, action.execution_errors()))
    logger.info("Conversions attempted/succeeded/failed: %d/%d/%d" % (len(actions), successes, failures))