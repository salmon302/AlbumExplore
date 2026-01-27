import logging
import sys
import os

sys.path.insert(0, os.path.abspath('src'))

from albumexplore.database import get_session, init_db
from albumexplore.visualization.data_interface import DataInterface
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.state import ViewType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('check_view_render')

def main():
    init_db()
    session = get_session()
    try:
        di = DataInterface(session)
        vm = ViewManager(di)
        rd = vm.switch_view(ViewType.TABLE)
        if not rd:
            logger.error('No render data returned')
            return
        rows = rd.get('rows', [])
        logger.info(f'Render data type: {rd.get("type")}, rows: {len(rows)}')
        if rows:
            for i, r in enumerate(rows[:5]):
                logger.info(f'Row {i}: id={r.get("id")}, artist={r.get("artist")}, album={r.get("album")}, year={r.get("year")}, tags_count={len(r.get("tags", []))}')
        else:
            logger.warning('Render returned zero rows')
    finally:
        session.close()

if __name__ == '__main__':
    main()
